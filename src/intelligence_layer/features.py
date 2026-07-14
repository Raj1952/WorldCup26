"""
Assemble the feature matrix from match_features table.

Outcome label encoding:
    0 = home win
    1 = draw
    2 = away win
"""

from __future__ import annotations

__all__ = ["build_feature_matrix", "FEATURE_COLS", "LABEL_MAP", "get_prediction_features"]

import sqlite3
import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

FEATURE_COLS = [
    "elo_diff",
    "elo_home",
    "elo_away",
    "form_diff",
    "form_home",
    "form_away",
    "gf_home",
    "ga_home",
    "gf_away",
    "ga_away",
    "rest_diff",
    "rest_home",
    "rest_away",
    "is_neutral",
    "is_knockout",
    "h2h_home_win_rate",
    "h2h_draw_rate",
    "h2h_away_win_rate",
    "h2h_n",
]

LABEL_MAP = {"home": 0, "draw": 1, "away": 2}
LABEL_INV = {0: "home", 1: "draw", 2: "away"}


def build_feature_matrix(
    db_path: str = "data/tempo.db",
    min_date: str | None = None,
    max_date: str | None = None,
    exclude_friendlies: bool = True,
) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    """
    Return (X, y, meta_df) for all matches with computed features.

    X  — float32 array shape (n, len(FEATURE_COLS))
    y  — int32 array shape (n,) with values 0/1/2
    meta_df — DataFrame with match_id, date, home_team, away_team

    Optionally filter by date range.  Never shuffles — caller controls splits.
    """
    conn = sqlite3.connect(db_path)

    query = (
        "SELECT f.*, m.stage, m.tournament FROM match_features f "
        "JOIN matches m ON f.match_id = m.match_id "
        "WHERE f.outcome IS NOT NULL"
    )
    params = []
    if exclude_friendlies:
        query += " AND m.stage != 'friendly'"
    if min_date:
        query += " AND f.date >= ?"
        params.append(min_date)
    if max_date:
        query += " AND f.date <= ?"
        params.append(max_date)
    query += " ORDER BY f.date ASC"

    df = pd.read_sql(query, conn, params=params)
    conn.close()

    if df.empty:
        return np.empty((0, len(FEATURE_COLS))), np.empty(0, dtype=int), df

    X = df[FEATURE_COLS].fillna(0).values.astype(np.float32)
    y = df["outcome"].map(LABEL_MAP).values.astype(np.int32)
    meta = df[["match_id", "date", "home_team", "away_team"]].reset_index(drop=True)

    logger.debug("Feature matrix: X=%s  y=%s", X.shape, y.shape)
    return X, y, meta


def get_prediction_features(
    home_team: str,
    away_team: str,
    date: str,
    is_neutral: bool,
    is_knockout: bool,
    db_path: str = "data/tempo.db",
) -> np.ndarray | None:
    """
    Build a single-row feature vector for an upcoming match.
    Returns None if not enough data is available.
    """
    from src.intelligence_layer.elo import get_current_elo
    from src.data_layer.build_features import _FORM_WINDOW, _GOALS_WINDOW, _H2H_WINDOW

    try:
        conn = sqlite3.connect(db_path)
        elo_h = get_current_elo(home_team, db_path)
        elo_a = get_current_elo(away_team, db_path)

        # All queries below read the raw `matches` table (actual scores), NOT
        # the derived match_features table, so serving-time features have the
        # exact same semantics as the deque-based training features in
        # src/data_layer/build_features.py.

        def last_matches(team: str, limit: int) -> pd.DataFrame:
            return pd.read_sql(
                "SELECT date, home_team, away_team, home_score, away_score, outcome "
                "FROM matches WHERE (home_team=? OR away_team=?) AND date < ? "
                f"ORDER BY date DESC LIMIT {limit}",
                conn, params=(team, team, date),
            )

        def form_query(team: str) -> float:
            rows = last_matches(team, _FORM_WINDOW)
            if rows.empty:
                return 0.5
            pts = []
            for _, r in rows.iterrows():   # newest first — weight 0.9**i, newest = 1.0
                if r["home_team"] == team:
                    pts.append({"home": 1.0, "draw": 0.5, "away": 0.0}.get(r["outcome"], 0.5))
                else:
                    pts.append({"home": 0.0, "draw": 0.5, "away": 1.0}.get(r["outcome"], 0.5))
            weights = [0.9 ** i for i in range(len(pts))]
            return sum(p * w for p, w in zip(pts, weights)) / sum(weights)

        def goals(team: str) -> tuple[float, float]:
            """(mean goals scored, mean goals conceded) over the last window."""
            rows = last_matches(team, _GOALS_WINDOW)
            if rows.empty:
                return 1.2, 1.2
            scored = rows.apply(
                lambda r: r["home_score"] if r["home_team"] == team else r["away_score"], axis=1
            )
            conceded = rows.apply(
                lambda r: r["away_score"] if r["home_team"] == team else r["home_score"], axis=1
            )
            return float(scored.mean()), float(conceded.mean())

        def rest_days(team: str) -> int:
            rows = last_matches(team, 1)
            if rows.empty:
                return 14
            last = pd.Timestamp(rows.iloc[0]["date"])
            return min(int((pd.Timestamp(date) - last).days), 30)

        def h2h_rates() -> tuple[float, float, float, int]:
            rows = pd.read_sql(
                "SELECT home_team, away_team, outcome FROM matches "
                "WHERE ((home_team=? AND away_team=?) OR (home_team=? AND away_team=?)) "
                f"AND date < ? ORDER BY date DESC LIMIT {_H2H_WINDOW}",
                conn, params=(home_team, away_team, away_team, home_team, date),
            )
            if rows.empty:
                return 0.0, 0.0, 0.0, 0    # matches training: empty history → all-zero rates
            n = len(rows)
            # Re-orient each past result to the CURRENT fixture's home team.
            winners = rows.apply(
                lambda r: r["home_team"] if r["outcome"] == "home"
                else r["away_team"] if r["outcome"] == "away" else "draw", axis=1
            )
            hw = (winners == home_team).sum() / n
            dw = (winners == "draw").sum() / n
            aw = (winners == away_team).sum() / n
            return float(hw), float(dw), float(aw), n

        form_h = form_query(home_team)
        form_a = form_query(away_team)
        gf_h, ga_h = goals(home_team)
        gf_a, ga_a = goals(away_team)
        rest_h = rest_days(home_team)
        rest_a = rest_days(away_team)
        h2h_hw, h2h_dw, h2h_aw, h2h_n = h2h_rates()
        conn.close()

        x = np.array([
            elo_h - elo_a, elo_h, elo_a,
            form_h - form_a, form_h, form_a,
            gf_h, ga_h, gf_a, ga_a,
            rest_h - rest_a, rest_h, rest_a,
            int(is_neutral), int(is_knockout),
            h2h_hw, h2h_dw, h2h_aw, h2h_n,
        ], dtype=np.float32).reshape(1, -1)
        return x
    except Exception as exc:
        logger.warning("get_prediction_features failed for %s vs %s: %s", home_team, away_team, exc)
        return None
