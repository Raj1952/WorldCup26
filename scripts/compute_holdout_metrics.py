"""
Compute RPS + calibration data on the training holdout set.

Writes to artifacts/reports/:
  holdout_summary.parquet     — scalar metrics (rps, log_loss, accuracy, brier)
  holdout_calibration.parquet — per-bin reliability data (3 outcome classes)
  holdout_confidence.parquet  — per-match max confidence values (for histogram)

Run after refresh.py or standalone:
  python scripts/compute_holdout_metrics.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.intelligence_layer.features import build_feature_matrix
from src.intelligence_layer.metrics import compute_rps, reliability_data, OUTCOME_LABELS
from src.intelligence_layer.registry import get_live_model

_TEST_START = "2018-01-01"
DB_PATH = "data/tempo.db"
REPORTS_DIR = Path("artifacts/reports")


def main() -> None:
    model, entry = get_live_model()
    if model is None:
        print("No live model found. Run pipelines/refresh.py first.")
        sys.exit(1)

    print(f"Model : {entry['version']}")

    X, y, meta = build_feature_matrix(DB_PATH, exclude_friendlies=True)
    split_idx = int((meta["date"] < _TEST_START).sum())
    if split_idx < 2500:
        split_idx = int(len(X) * 0.8)

    X_test = X[split_idx:]
    y_test = y[split_idx:]
    dates = meta["date"].values[split_idx:]
    print(f"Holdout: {len(X_test)} rows  ({dates[0]} to {dates[-1]})")

    proba = model.predict_proba(X_test)

    rps = compute_rps(y_test, proba)
    print(f"\nRPS        : {rps:.4f}  (uniform baseline ~0.3333)")
    print(f"Log-loss   : {entry.get('log_loss_test', 0):.4f}")
    print(f"Accuracy   : {entry.get('accuracy_test', 0):.1%}  (secondary)")
    print(f"Brier      : {entry.get('brier_test', 0):.4f}")

    rel = reliability_data(y_test, proba, n_bins=10)

    # — calibration rows (one per bin × class) —
    cal_rows = []
    for b, center in enumerate(rel.bin_centers):
        for c, label in enumerate(["home", "draw", "away"]):
            mp = rel.mean_pred[b, c]
            of = rel.obs_freq[b, c]
            cal_rows.append({
                "bin_center": float(center),
                "outcome": label,
                "mean_pred": float(mp) if not np.isnan(mp) else None,
                "obs_freq": float(of) if not np.isnan(of) else None,
                "bin_count": int(rel.bin_counts[b, c]),
            })

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(cal_rows).to_parquet(REPORTS_DIR / "holdout_calibration.parquet", index=False)
    pd.DataFrame({"confidence": rel.conf_values}).to_parquet(
        REPORTS_DIR / "holdout_confidence.parquet", index=False
    )
    pd.DataFrame([{
        "rps_test": rps,
        "log_loss_test": entry.get("log_loss_test"),
        "accuracy_test": entry.get("accuracy_test"),
        "brier_test": entry.get("brier_test"),
        "n_test": len(X_test),
        "model_version": entry["version"],
        "created_at": entry.get("created_at", ""),
    }]).to_parquet(REPORTS_DIR / "holdout_summary.parquet", index=False)

    print(f"\nArtifacts written to {REPORTS_DIR}/")


if __name__ == "__main__":
    main()
