"""
Generate predictions.parquet for all upcoming WC2026 matches.

Output contract (one row per unplayed match):
  match_id, date, home_team, away_team,
  p_home, p_draw, p_away,
  top_factors (JSON list), model_version, created_at
"""

from __future__ import annotations

__all__ = ["predict_upcoming"]

import json
import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Bracket slot identifiers — any team name that starts with a digit (e.g. "1A", "3A/B/C")
# or looks like a match-code (e.g. "L101", "W102").  These have no real team behind them.
_SLOT_RE = re.compile(r"^[0-9]|^[A-Z]\d{3,}$")


def _is_concrete_team(name: str) -> bool:
    """True for a real team name; False for bracket slot codes like '1A', '3A/B/C', 'L101'."""
    return not _SLOT_RE.match(name)

from .features import get_prediction_features, FEATURE_COLS
from .explain import explain_single
from .registry import get_live_model

logger = logging.getLogger(__name__)

PREDICTIONS_PATH = Path("predictions.parquet")


def predict_upcoming(db_path: str = "data/tempo.db") -> pd.DataFrame:
    """
    Load live model, run predictions for all scheduled WC2026 fixtures,
    write predictions.parquet.  Returns the predictions DataFrame.
    """
    model, meta = get_live_model()
    if model is None:
        logger.error("No live model in registry — run training first.")
        return pd.DataFrame()

    model_version = meta["version"]
    now = datetime.utcnow().isoformat()

    # Filter: "no final result yet" — NOT "date in the future".
    # This ensures a match that hasn't kicked off (even if dated yesterday,
    # e.g. a late-ingest fixture) still gets a real model prediction instead
    # of falling back to Elo in the Monte Carlo sim.  Matches are excluded
    # only once home_score is recorded (result is final).
    # Placeholder slots (W%) are skipped — they have no concrete teams yet.
    conn = sqlite3.connect(db_path)
    fixtures = pd.read_sql(
        "SELECT match_id,date,kickoff_time,home_team,away_team,group_label "
        "FROM wc2026_fixtures "
        "WHERE home_score IS NULL "
        "  AND home_team NOT LIKE 'W%' "
        "  AND away_team NOT LIKE 'W%' "
        "ORDER BY date ASC",
        conn,
    )
    conn.close()

    if fixtures.empty:
        logger.warning("No upcoming fixtures found in wc2026_fixtures table.")
        return pd.DataFrame()

    logger.info("Predicting %d upcoming fixtures …", len(fixtures))
    rows = []

    for _, fix in fixtures.iterrows():
        home = fix["home_team"]
        away = fix["away_team"]
        date = fix["date"]
        is_knockout = fix["group_label"] not in list("ABCDEFGHIJKL")

        # Bracket-slot fixtures have no concrete teams yet — suppress probabilities
        # so downstream views cannot accidentally display a fake-looking forecast.
        is_projected = not (_is_concrete_team(home) and _is_concrete_team(away))
        if is_projected:
            rows.append({
                "match_id":    fix["match_id"],
                "date":        date,
                "kickoff_time": fix.get("kickoff_time", "00:00"),
                "home_team":   home,
                "away_team":   away,
                "group_label": fix["group_label"],
                "is_projected": True,
                "p_home":      float("nan"),
                "p_draw":      float("nan"),
                "p_away":      float("nan"),
                "top_factors": "[]",
                "model_version": model_version,
                "created_at":  now,
            })
            continue

        x = get_prediction_features(
            home_team=home,
            away_team=away,
            date=date,
            is_neutral=True,         # WC2026 venues are nominally neutral
            is_knockout=is_knockout,
            db_path=db_path,
        )
        if x is None:
            logger.warning("Skipping %s vs %s — features not available", home, away)
            continue

        proba = model.predict_proba(x)[0]
        p_home = float(proba[0])
        p_draw = float(proba[1])
        p_away = float(proba[2])

        factors = explain_single(model, x, FEATURE_COLS, top_n=3)

        rows.append({
            "match_id":    fix["match_id"],
            "date":        date,
            "kickoff_time": fix.get("kickoff_time", "00:00"),
            "home_team":   home,
            "away_team":   away,
            "group_label": fix["group_label"],
            "is_projected": False,
            "p_home":      round(p_home, 4),
            "p_draw":      round(p_draw, 4),
            "p_away":      round(p_away, 4),
            "top_factors": json.dumps(factors),
            "model_version": model_version,
            "created_at":  now,
        })

    if not rows:
        logger.warning("No predictions generated.")
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df.to_parquet(PREDICTIONS_PATH, index=False)
    logger.info("Wrote %d predictions → %s", len(df), PREDICTIONS_PATH)
    return df


def load_predictions() -> pd.DataFrame:
    """Load and return predictions.parquet, or empty DataFrame if not found."""
    if not PREDICTIONS_PATH.exists():
        return pd.DataFrame()
    df = pd.read_parquet(PREDICTIONS_PATH)
    df["top_factors"] = df["top_factors"].apply(
        lambda x: json.loads(x) if isinstance(x, str) else (x or [])
    )
    return df
