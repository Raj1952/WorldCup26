"""
Per-team Elo rating, computed match-by-match in strict chronological order.

K-factor schedule:
  60  → FIFA World Cup final / semi
  50  → FIFA World Cup other knockout
  40  → FIFA World Cup group / continental championship knockout
  35  → Continental championship group / CONCACAF/AFC cup
  30  → Other competitive internationals
  20  → Friendly

Home-field advantage: +100 Elo points added to home team's effective rating
(unless neutral venue).
"""

from __future__ import annotations

__all__ = ["compute_elo_ratings", "expected_score", "update_elo"]

import logging
import sqlite3
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_INITIAL_ELO = 1500.0
_HOME_ADVANTAGE = 100.0  # effective Elo bonus for home team on non-neutral ground

_K_MAP = {
    "wc_final": 60,
    "wc_knockout": 50,
    "wc_group": 40,
    "continental_knockout": 40,
    "continental_group": 35,
    "competitive": 30,
    "friendly": 20,
}


def _k_factor(tournament: str, stage: str) -> float:
    t = (tournament or "").lower()
    s = (stage or "").lower()
    if "world cup" in t:
        if s == "knockout" and ("final" in t or "final" in s):
            return _K_MAP["wc_final"]
        if s == "knockout":
            return _K_MAP["wc_knockout"]
        return _K_MAP["wc_group"]
    if any(x in t for x in ("euro", "copa america", "africa cup", "asian cup",
                              "concacaf gold", "nations league")):
        if s == "knockout":
            return _K_MAP["continental_knockout"]
        return _K_MAP["continental_group"]
    if s == "friendly" or "friendly" in t:
        return _K_MAP["friendly"]
    return _K_MAP["competitive"]


def expected_score(elo_a: float, elo_b: float) -> float:
    """Expected score for team A vs team B (0–1, i.e. win probability)."""
    return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / 400.0))


def update_elo(
    elo_home: float,
    elo_away: float,
    outcome: str,       # 'home' | 'draw' | 'away'
    k: float,
    is_neutral: bool,
) -> tuple[float, float]:
    """Return (new_home_elo, new_away_elo) after a match."""
    effective_home = elo_home + (0 if is_neutral else _HOME_ADVANTAGE)
    e_home = expected_score(effective_home, elo_away)
    e_away = 1.0 - e_home

    actual_home = {"home": 1.0, "draw": 0.5, "away": 0.0}[outcome]
    actual_away = 1.0 - actual_home

    new_home = elo_home + k * (actual_home - e_home)
    new_away = elo_away + k * (actual_away - e_away)
    return new_home, new_away


def compute_elo_ratings(db_path: str = "data/tempo.db") -> None:
    """
    Compute Elo for every team in chronological order, store in `elo_ratings`.
    Idempotent: drops and rewrites the table each run.
    """
    conn = sqlite3.connect(db_path)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS elo_ratings (
            team   TEXT NOT NULL,
            date   TEXT NOT NULL,
            elo    REAL NOT NULL,
            PRIMARY KEY (team, date)
        )
    """)
    # Full recompute — wipe existing ratings
    conn.execute("DELETE FROM elo_ratings")
    conn.commit()

    df = pd.read_sql(
        "SELECT date,home_team,away_team,outcome,tournament,is_neutral,stage "
        "FROM matches ORDER BY date ASC",
        conn,
    )
    logger.info("Computing Elo over %d matches …", len(df))

    ratings: dict[str, float] = {}

    def get_elo(team: str) -> float:
        return ratings.get(team, _INITIAL_ELO)

    rows = []
    for _, row in df.iterrows():
        home, away = row["home_team"], row["away_team"]
        outcome = row["outcome"]
        is_neutral = bool(row["is_neutral"])
        k = _k_factor(row["tournament"], row["stage"])

        elo_h = get_elo(home)
        elo_a = get_elo(away)

        new_h, new_a = update_elo(elo_h, elo_a, outcome, k, is_neutral)
        ratings[home] = new_h
        ratings[away] = new_a

        rows.append({"team": home, "date": row["date"], "elo": new_h})
        rows.append({"team": away, "date": row["date"], "elo": new_a})

    if rows:
        elo_df = pd.DataFrame(rows)
        # keep last rating per (team, date) in case multiple matches on same day
        elo_df = elo_df.groupby(["team", "date"]).last().reset_index()
        elo_df.to_sql("elo_ratings", conn, if_exists="replace", index=False)

    conn.commit()
    conn.close()

    # Store current ratings separately for quick lookup
    _write_current_ratings(db_path, ratings)
    logger.info("Elo computation complete.  %d teams rated.", len(ratings))


def _write_current_ratings(db_path: str, ratings: dict[str, float]) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS elo_current (
            team TEXT PRIMARY KEY,
            elo  REAL NOT NULL
        )
    """)
    conn.execute("DELETE FROM elo_current")
    conn.executemany(
        "INSERT INTO elo_current(team,elo) VALUES(?,?)",
        [(t, e) for t, e in ratings.items()],
    )
    conn.commit()
    conn.close()


def get_current_elo(team: str, db_path: str = "data/tempo.db") -> float:
    """Return most recent Elo for a team, or initial value if not found."""
    try:
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT elo FROM elo_current WHERE team=?", (team,)
        ).fetchone()
        conn.close()
        return row[0] if row else _INITIAL_ELO
    except Exception:
        return _INITIAL_ELO
