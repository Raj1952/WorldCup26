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
import sqlite3
from datetime import datetime, date as Date
from pathlib import Path

import numpy as np
import pandas as pd

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
    today = str(Date.today())

    conn = sqlite3.connect(db_path)
    fixtures = pd.read_sql(
        "SELECT match_id,date,kickoff_time,home_team,away_team,group_label "
        "FROM wc2026_fixtures WHERE status='scheduled' AND date >= ? "
        "ORDER BY date ASC",
        conn,
        params=(today,),
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
        # Ensure order: [home=0, draw=1, away=2]
        p_home = float(proba[0])
        p_draw = float(proba[1])
        p_away = float(proba[2])

        factors = explain_single(model, x, FEATURE_COLS, top_n=3)

        rows.append({
            "match_id": fix["match_id"],
            "date": date,
            "kickoff_time": fix.get("kickoff_time", "00:00"),
            "home_team": home,
            "away_team": away,
            "group_label": fix["group_label"],
            "p_home": round(p_home, 4),
            "p_draw": round(p_draw, 4),
            "p_away": round(p_away, 4),
            "top_factors": json.dumps(factors),
            "model_version": model_version,
            "created_at": now,
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
