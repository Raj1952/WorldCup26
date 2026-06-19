"""
Evaluation metrics for ordered 3-class probabilistic forecasts.

Outcomes are ordered: 0=Home Win, 1=Draw, 2=Away Win.
RPS is the primary metric per §0.5. Accuracy is secondary-only.
"""

from __future__ import annotations

__all__ = ["compute_rps", "reliability_data", "ReliabilityData"]

from typing import NamedTuple

import numpy as np

OUTCOME_LABELS = ["Home Win", "Draw", "Away Win"]
OUTCOME_COLORS = ["#1FB479", "#3E7BFA", "#E4564A"]


def compute_rps(y_true: np.ndarray, proba: np.ndarray) -> float:
    """
    Ranked Probability Score for an ordered 3-outcome forecast.

    Lower is better; perfect forecast = 0.
    Uniform baseline (1/3, 1/3, 1/3) scores ≈ 0.333.

    y_true : 1-D int array, values in {0, 1, 2}
    proba  : (n, 3) float array, rows summing to 1
    """
    K = proba.shape[1]
    cum_pred = np.cumsum(proba[:, : K - 1], axis=1)          # (n, K-1)
    cum_actual = np.column_stack(
        [(y_true <= k).astype(float) for k in range(K - 1)]  # (n, K-1)
    )
    rps = float(np.mean(np.sum((cum_pred - cum_actual) ** 2, axis=1) / (K - 1)))
    return rps


class ReliabilityData(NamedTuple):
    bin_centers: np.ndarray   # (n_bins,)  midpoint of each probability bin
    mean_pred: np.ndarray     # (n_bins, 3)  mean predicted probability per bin, per class
    obs_freq: np.ndarray      # (n_bins, 3)  observed frequency per bin, per class
    bin_counts: np.ndarray    # (n_bins, 3)  sample count per bin, per class
    conf_values: np.ndarray   # (n,)  max probability per match (model confidence)


def reliability_data(
    y_true: np.ndarray,
    proba: np.ndarray,
    n_bins: int = 10,
) -> ReliabilityData:
    """
    Compute calibration data for a reliability diagram.

    For each class, bin predicted probabilities into n_bins equal-width
    buckets and compute mean predicted vs observed frequency in each bucket.
    """
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2.0
    K = proba.shape[1]

    mean_pred = np.full((n_bins, K), np.nan)
    obs_freq = np.full((n_bins, K), np.nan)
    bin_counts = np.zeros((n_bins, K), dtype=int)

    for c in range(K):
        p_c = proba[:, c]
        y_c = (y_true == c).astype(float)
        for b in range(n_bins):
            lo, hi = edges[b], edges[b + 1]
            mask = (p_c >= lo) & (p_c < hi) if b < n_bins - 1 else (p_c >= lo) & (p_c <= hi)
            cnt = int(mask.sum())
            bin_counts[b, c] = cnt
            if cnt > 0:
                mean_pred[b, c] = float(p_c[mask].mean())
                obs_freq[b, c] = float(y_c[mask].mean())

    return ReliabilityData(
        bin_centers=centers,
        mean_pred=mean_pred,
        obs_freq=obs_freq,
        bin_counts=bin_counts,
        conf_values=proba.max(axis=1),
    )
