"""
Train baseline (Elo-logistic) and full (XGBoost) models.

Time-based splits only — never random K-fold.
Baseline must be beaten before XGBoost is promoted.
"""

from __future__ import annotations

__all__ = ["train_baseline", "train_xgboost", "evaluate_model", "TrainingResult",
           "time_split", "BaselineWrapper"]

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, accuracy_score, brier_score_loss
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

import xgboost as xgb

from .features import build_feature_matrix, FEATURE_COLS

logger = logging.getLogger(__name__)

# Three-way chronological split (train / calibration / frozen test).
# Calibration must NEVER overlap train (isotonic would leak) and test must
# NEVER be used for fitting anything — it is the frozen promotion yardstick.
_CAL_START = "2018-01-01"    # train:  date <  _CAL_START
_TEST_START = "2023-01-01"   # cal:    _CAL_START <= date < _TEST_START
                             # test:   date >= _TEST_START
_MIN_TRAIN_SIZE = 5000  # refuse to train if fewer rows
_MIN_SEGMENT = 500      # fall back to proportional split below this


def time_split(
    X: np.ndarray, y: np.ndarray, meta,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Chronological train / calibration / test split.

    Returns (X_train, y_train, X_cal, y_cal, X_test, y_test).
    Falls back to a proportional 70/15/15 split if any date segment is
    too small (e.g. synthetic test databases).
    """
    dates = meta["date"].values
    n_train = int((dates < _CAL_START).sum())
    n_cal_end = int((dates < _TEST_START).sum())

    if (n_train < _MIN_SEGMENT
            or (n_cal_end - n_train) < _MIN_SEGMENT
            or (len(X) - n_cal_end) < _MIN_SEGMENT):
        n_train = int(len(X) * 0.70)
        n_cal_end = int(len(X) * 0.85)

    return (X[:n_train], y[:n_train],
            X[n_train:n_cal_end], y[n_train:n_cal_end],
            X[n_cal_end:], y[n_cal_end:])


class BaselineWrapper:
    """Column-subset adapter so the baseline accepts the full feature matrix.

    Module-level on purpose: locally-defined classes cannot be pickled, which
    corrupted registry artifacts and could kill prediction serving."""

    def __init__(self, inner, cols):
        self._inner = inner
        self._cols = cols

    def predict(self, X):
        return self._inner.predict(X[:, self._cols])

    def predict_proba(self, X):
        return self._inner.predict_proba(X[:, self._cols])


@dataclass
class TrainingResult:
    model: object
    model_type: str      # 'baseline' or 'xgboost'
    log_loss_train: float
    log_loss_test: float
    accuracy_test: float
    brier_test: float
    n_train: int
    n_test: int
    feature_importances: dict = field(default_factory=dict)
    trained_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


def evaluate_model(model, X_test: np.ndarray, y_test: np.ndarray) -> dict:
    proba = model.predict_proba(X_test)
    classes = [0, 1, 2]
    ll = log_loss(y_test, proba, labels=classes)
    acc = accuracy_score(y_test, model.predict(X_test))
    # Brier score averaged across classes
    brier = float(np.mean([
        brier_score_loss((y_test == c).astype(int), proba[:, i])
        for i, c in enumerate(classes)
    ]))
    return {"log_loss": ll, "accuracy": acc, "brier": brier}


def train_baseline(db_path: str = "data/tempo.db") -> TrainingResult:
    """Elo-diff + form logistic regression — the bar XGBoost must beat."""
    X, y, meta = build_feature_matrix(db_path, exclude_friendlies=True)
    if len(X) < _MIN_TRAIN_SIZE:
        raise RuntimeError(f"Only {len(X)} training rows — run ingest first.")

    X_train, y_train, _X_cal, _y_cal, X_test, y_test = time_split(X, y, meta)

    # Baseline only uses Elo + form features
    baseline_cols = [0, 1, 2, 3, 4, 5]  # elo_diff, elo_home, elo_away, form_diff, form_home, form_away
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(max_iter=500, C=1.0)),
    ])
    model.fit(X_train[:, baseline_cols], y_train)

    wrapped = BaselineWrapper(model, baseline_cols)
    metrics_train = evaluate_model(wrapped, X_train, y_train)
    metrics_test = evaluate_model(wrapped, X_test, y_test)

    logger.info(
        "Baseline: log_loss=%.4f (train) / %.4f (test)  acc=%.3f",
        metrics_train["log_loss"], metrics_test["log_loss"], metrics_test["accuracy"],
    )
    return TrainingResult(
        model=wrapped,
        model_type="baseline",
        log_loss_train=metrics_train["log_loss"],
        log_loss_test=metrics_test["log_loss"],
        accuracy_test=metrics_test["accuracy"],
        brier_test=metrics_test["brier"],
        n_train=len(X_train),
        n_test=len(X_test),
    )


def train_xgboost(db_path: str = "data/tempo.db") -> TrainingResult:
    """Full XGBoost 3-class model on all leak-free features."""
    X, y, meta = build_feature_matrix(db_path, exclude_friendlies=True)
    if len(X) < _MIN_TRAIN_SIZE:
        raise RuntimeError(f"Only {len(X)} training rows — run ingest first.")

    X_train, y_train, X_cal, y_cal, X_test, y_test = time_split(X, y, meta)

    model = xgb.XGBClassifier(
        n_estimators=400,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        gamma=0.1,
        objective="multi:softprob",
        num_class=3,
        eval_metric="mlogloss",
        random_state=42,
        n_jobs=-1,
    )
    # Monitor on the calibration slice — the test slice stays untouched by training.
    eval_set = [(X_train, y_train), (X_cal, y_cal)]
    model.fit(
        X_train, y_train,
        eval_set=eval_set,
        verbose=False,
    )

    metrics_train = evaluate_model(model, X_train, y_train)
    metrics_test = evaluate_model(model, X_test, y_test)

    fi = dict(zip(FEATURE_COLS, model.feature_importances_.tolist()))

    logger.info(
        "XGBoost: log_loss=%.4f (train) / %.4f (test)  acc=%.3f",
        metrics_train["log_loss"], metrics_test["log_loss"], metrics_test["accuracy"],
    )
    return TrainingResult(
        model=model,
        model_type="xgboost",
        log_loss_train=metrics_train["log_loss"],
        log_loss_test=metrics_test["log_loss"],
        accuracy_test=metrics_test["accuracy"],
        brier_test=metrics_test["brier"],
        n_train=len(X_train),
        n_test=len(X_test),
        feature_importances=fi,
    )
