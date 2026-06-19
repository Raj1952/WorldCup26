"""
Isotonic calibration for multi-class probability outputs.
sklearn 1.9 removed cv='prefit' from CalibratedClassifierCV, so we
implement a lightweight per-class isotonic wrapper instead.
"""

from __future__ import annotations

__all__ = ["calibrate_model"]

import logging
import numpy as np
from sklearn.isotonic import IsotonicRegression

logger = logging.getLogger(__name__)


class _IsotonicCalibrator:
    """Per-class isotonic regression calibration for a pre-fitted classifier."""

    def __init__(self, base_model, X_cal: np.ndarray, y_cal: np.ndarray):
        self._base = base_model
        self._isos: list[IsotonicRegression] = []

        raw_proba = base_model.predict_proba(X_cal)
        n_classes = raw_proba.shape[1]
        for c in range(n_classes):
            iso = IsotonicRegression(out_of_bounds="clip")
            iso.fit(raw_proba[:, c], (y_cal == c).astype(float))
            self._isos.append(iso)

        logger.info("Calibrated %d classes on %d samples.", n_classes, len(y_cal))

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        raw = self._base.predict_proba(X)
        cal = np.column_stack([
            self._isos[c].transform(raw[:, c]) for c in range(raw.shape[1])
        ])
        # Normalise rows to sum to 1
        row_sums = cal.sum(axis=1, keepdims=True)
        return cal / np.maximum(row_sums, 1e-8)

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.predict_proba(X).argmax(axis=1)


def calibrate_model(model, X_cal: np.ndarray, y_cal: np.ndarray) -> _IsotonicCalibrator:
    """
    Return an isotonically-calibrated wrapper around a pre-fitted model.
    Works with any model that exposes predict_proba().
    """
    return _IsotonicCalibrator(model, X_cal, y_cal)
