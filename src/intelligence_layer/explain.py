"""
Per-prediction feature explanations using XGBoost native pred_contribs.

Falls back to global feature importances if the model is not XGBoost.
"""

from __future__ import annotations

__all__ = ["explain_predictions", "explain_single"]

import logging
import numpy as np

logger = logging.getLogger(__name__)

FEATURE_LABELS = {
    "elo_diff":          "Elo rating gap",
    "elo_home":          "Home team Elo",
    "elo_away":          "Away team Elo",
    "form_diff":         "Recent form edge",
    "form_home":         "Home recent form",
    "form_away":         "Away recent form",
    "gf_home":           "Home goals scored",
    "ga_home":           "Home goals conceded",
    "gf_away":           "Away goals scored",
    "ga_away":           "Away goals conceded",
    "rest_diff":         "Rest day advantage",
    "rest_home":         "Home rest days",
    "rest_away":         "Away rest days",
    "is_neutral":        "Neutral venue",
    "is_knockout":       "Knockout stage",
    "h2h_home_win_rate": "H2H home record",
    "h2h_draw_rate":     "H2H draw tendency",
    "h2h_away_win_rate": "H2H away record",
    "h2h_n":             "Head-to-head history",
}


def _unwrap_xgb(model):
    """Dig through calibrator wrappers to find the raw XGBClassifier."""
    import xgboost as xgb
    for attr in ("_base", "base_estimator", "estimator", "calibrated_classifiers_"):
        candidate = getattr(model, attr, None)
        if candidate is not None:
            if isinstance(candidate, xgb.XGBClassifier):
                return candidate
            # one more level
            for attr2 in ("_base", "base_estimator", "estimator"):
                inner2 = getattr(candidate, attr2, None)
                if isinstance(inner2, xgb.XGBClassifier):
                    return inner2
    if isinstance(model, xgb.XGBClassifier):
        return model
    return None


def explain_predictions(
    model,
    X: np.ndarray,
    feature_names: list[str],
    top_n: int = 3,
) -> list[list[dict]]:
    """
    Return per-row factor lists.  Uses XGBoost pred_contribs (fast, reliable).
    Falls back to global importances if XGBoost is not available.
    """
    import xgboost as xgb

    inner = _unwrap_xgb(model)

    if inner is not None:
        return _explain_xgb_contribs(inner, X, feature_names, top_n)
    else:
        logger.warning("Non-XGBoost model — using global importances as factors")
        return _explain_importances(model, X, feature_names, top_n)


def _explain_xgb_contribs(
    xgb_model,
    X: np.ndarray,
    feature_names: list[str],
    top_n: int,
) -> list[list[dict]]:
    """
    Use XGBoost's built-in pred_contribs for per-prediction explanations.
    Returns (n_samples, n_features+1, n_classes) — last column is bias; we drop it.
    Direction is based on the contribution to class 0 (home win).
    """
    import xgboost as xgb

    try:
        dmat = xgb.DMatrix(X, feature_names=feature_names)
        # shape: (n_samples, n_features+1, n_classes)
        contribs = xgb_model.get_booster().predict(dmat, pred_contribs=True)

        results = []
        for i in range(len(X)):
            row = contribs[i]              # (n_features+1, n_classes) or (n_features+1,)
            if row.ndim == 1:
                row = row[:-1]             # drop bias, shape (n_features,)
                abs_sum = np.abs(row)
                dir_vals = row
            else:
                row = row[:-1, :]          # drop bias row → (n_features, n_classes)
                abs_sum = np.abs(row).sum(axis=1)   # total |contribution| per feature
                dir_vals = row[:, 0]       # direction relative to home-win class

            top_idx = np.argsort(abs_sum)[::-1][:top_n]
            factors = []
            for idx in top_idx:
                if idx >= len(feature_names):
                    continue
                name = feature_names[idx]
                label = FEATURE_LABELS.get(name, name)
                direction = "+" if float(dir_vals[idx]) >= 0 else "-"
                factors.append({
                    "label": label,
                    "feature": name,
                    "direction": direction,
                    "impact": float(abs_sum[idx]),
                })
            results.append(factors)
        return results

    except Exception as exc:
        logger.warning("pred_contribs failed: %s — using global importances", exc)
        return _explain_importances(xgb_model, X, feature_names, top_n)


def _explain_importances(
    model,
    X: np.ndarray,
    feature_names: list[str],
    top_n: int,
) -> list[list[dict]]:
    """Fallback: use global feature importances + feature value sign for direction."""
    try:
        importances = model.feature_importances_
    except AttributeError:
        return [[] for _ in range(len(X))]

    top_idx = np.argsort(importances)[::-1][:top_n]
    results = []
    for i in range(len(X)):
        x_row = X[i]
        factors = []
        for idx in top_idx:
            if idx >= len(feature_names):
                continue
            name = feature_names[idx]
            label = FEATURE_LABELS.get(name, name)
            direction = "+" if float(x_row[idx]) >= 0 else "-"
            factors.append({
                "label": label,
                "feature": name,
                "direction": direction,
                "impact": float(importances[idx]),
            })
        results.append(factors)
    return results


def explain_single(
    model,
    x: np.ndarray,
    feature_names: list[str],
    top_n: int = 3,
) -> list[dict]:
    result = explain_predictions(model, x.reshape(1, -1), feature_names, top_n)
    return result[0] if result else []
