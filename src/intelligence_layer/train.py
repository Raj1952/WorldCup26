"""
Train baseline (Elo-logistic) and full (XGBoost) models.

Time-based splits only — never random K-fold.
Baseline must be beaten before XGBoost is promoted.
"""

from __future__ import annotations

__all__ = ["train_baseline", "train_xgboost", "evaluate_model", "TrainingResult"]

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

# Time split: train on everything before this date, test on after
_TEST_START = "2018-01-01"
# WC2026 is ongoing: final train cutoff is yesterday (pipeline caller sets this)
_MIN_TRAIN_SIZE = 5000  # refuse to train if fewer rows


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

    split_idx = (meta["date"] < _TEST_START).sum()
    if split_idx < _MIN_TRAIN_SIZE // 2:
        split_idx = int(len(X) * 0.8)

    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    # Baseline only uses Elo-related features (cols 0-2 = elo_diff, elo_home, elo_away)
    baseline_cols = [0, 1, 2, 3, 4, 5]  # elo_diff, elo_home, elo_away, form_diff, form_home, form_away
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(max_iter=500, C=1.0)),
    ])
    model.fit(X_train[:, baseline_cols], y_train)

    # Wrap to handle full feature matrix
    class BaselineWrapper:
        def __init__(self, inner, cols):
            self._inner = inner
            self._cols = cols
        def predict(self, X):
            return self._inner.predict(X[:, self._cols])
        def predict_proba(self, X):
            return self._inner.predict_proba(X[:, self._cols])

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

    split_idx = (meta["date"] < _TEST_START).sum()
    if split_idx < _MIN_TRAIN_SIZE // 2:
        split_idx = int(len(X) * 0.8)

    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

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
    eval_set = [(X_train, y_train), (X_test, y_test)]
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
