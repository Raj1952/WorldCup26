"""
Private prediction-vs-result archive.

Appends to artifacts/private/results_log.csv and writes a daily
snapshot JSON.  Never imported by or visible in the presentation layer.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PRIVATE_DIR = Path("artifacts/private")
CSV_PATH    = PRIVATE_DIR / "results_log.csv"


def _rps(p_home: float, p_draw: float, p_away: float, actual: str) -> float:
    """Ranked Probability Score for one 3-outcome prediction."""
    o_h  = 1.0 if actual == "home" else 0.0
    o_hd = 1.0 if actual in ("home", "draw") else 0.0
    cp_h  = p_home
    cp_hd = p_home + p_draw
    return 0.5 * ((cp_h - o_h) ** 2 + (cp_hd - o_hd) ** 2)


def _outcome(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "home"
    if home_score < away_score:
        return "away"
    return "draw"


def run_archive(db_path: str = "data/tempo.db",
                preds_path: str = "predictions.parquet") -> int:
    """
    Find predictions that now have results, append new ones to CSV,
    write a daily JSON snapshot.  Returns the number of new records saved.
    """
    from src.data_layer.team_aliases import get_flag_code

    preds = pd.read_parquet(preds_path)

    con = sqlite3.connect(db_path)
    fixtures = pd.read_sql(
        "SELECT match_id, home_score, away_score FROM wc2026_fixtures WHERE status='played'",
        con,
    )
    con.close()

    merged = preds.merge(fixtures, on="match_id", how="inner")
    if merged.empty:
        return 0

    # Load existing CSV to skip already-archived match_ids
    existing_ids: set[str] = set()
    if CSV_PATH.exists():
        existing_ids = set(pd.read_csv(CSV_PATH)["match_id"].astype(str))

    new_rows = []
    for _, r in merged.iterrows():
        if r["match_id"] in existing_ids:
            continue
        p_h, p_d, p_a = float(r["p_home"]), float(r["p_draw"]), float(r["p_away"])
        actual = _outcome(int(r["home_score"]), int(r["away_score"]))
        probs  = {"home": p_h, "draw": p_d, "away": p_a}
        pred   = max(probs, key=probs.__getitem__)
        new_rows.append({
            "match_id":            r["match_id"],
            "date":                r["date"],
            "home_team":           r["home_team"],
            "away_team":           r["away_team"],
            "home_flag_code":      get_flag_code(r["home_team"]),
            "away_flag_code":      get_flag_code(r["away_team"]),
            "p_home":              round(p_h, 4),
            "p_draw":              round(p_d, 4),
            "p_away":              round(p_a, 4),
            "predicted_outcome":   pred,
            "predicted_confidence": round(probs[pred], 4),
            "actual_home_score":   int(r["home_score"]),
            "actual_away_score":   int(r["away_score"]),
            "actual_outcome":      actual,
            "correct":             pred == actual,
            "rps_this_match":      round(_rps(p_h, p_d, p_a, actual), 6),
        })

    if not new_rows:
        return 0

    PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    batch = pd.DataFrame(new_rows)
    batch.to_csv(CSV_PATH, mode="a", header=not CSV_PATH.exists(), index=False)

    # Daily JSON snapshot
    all_log = pd.read_csv(CSV_PATH)
    n_correct = int(all_log["correct"].sum())
    n_total   = len(all_log)
    cum_rps   = round(float(all_log["rps_this_match"].mean()), 6)
    snapshot  = {
        "generated_at":  datetime.now(timezone.utc).isoformat(),
        "batch_date":    str(batch["date"].max()),
        "new_records":   new_rows,
        "cumulative": {
            "total_predicted": n_total,
            "total_correct":   n_correct,
            "accuracy":        round(n_correct / n_total, 4) if n_total else 0,
            "mean_rps":        cum_rps,
        },
    }
    date_tag  = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    snap_path = PRIVATE_DIR / f"matchday_{date_tag}.json"
    snap_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    return len(new_rows)
