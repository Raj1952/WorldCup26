"""
Compute leak-free pre-match feature tables and store to tempo.db.

All features use only information available BEFORE kickoff.
Chronological computation — no shuffling, no look-ahead.
"""

from __future__ import annotations

__all__ = ["build_features"]

import logging
import sqlite3
from collections import defaultdict, deque

import pandas as pd

from src.intelligence_layer.elo import compute_elo_ratings

logger = logging.getLogger(__name__)

_FORM_WINDOW = 5        # last N matches for form
_GOALS_WINDOW = 5       # last N matches for rolling goals
_H2H_WINDOW = 10        # last N head-to-head meetings


def build_features(db_path: str = "data/tempo.db") -> None:
    """
    Compute and store the `match_features` table in tempo.db.
    Call AFTER both ingest steps so the matches table is populated.
    """
    # Step 1: compute / refresh Elo ratings
    compute_elo_ratings(db_path)

    conn = sqlite3.connect(db_path)
    df = pd.read_sql(
        "SELECT match_id,date,home_team,away_team,home_score,away_score,"
        "outcome,tournament,is_neutral,stage "
        "FROM matches ORDER BY date ASC",
        conn,
    )
    logger.info("Building features for %d matches …", len(df))

    # Per-team sliding windows (populated strictly BEFORE each match)
    form: dict[str, deque] = defaultdict(lambda: deque(maxlen=_FORM_WINDOW))
    gf: dict[str, deque] = defaultdict(lambda: deque(maxlen=_GOALS_WINDOW))
    ga: dict[str, deque] = defaultdict(lambda: deque(maxlen=_GOALS_WINDOW))
    last_played: dict[str, str] = {}
    h2h: dict[tuple, deque] = defaultdict(lambda: deque(maxlen=_H2H_WINDOW))

    # Elo snapshot per team per date — read from DB
    elo_df = pd.read_sql(
        "SELECT team,date,elo FROM elo_ratings ORDER BY date ASC", conn
    )
    elo_map: dict[tuple, float] = {
        (row.team, row.date): row.elo for row in elo_df.itertuples()
    }

    def get_elo_at(team: str, date: str) -> float:
        """Return Elo for team as of the given date (latest rating <= date)."""
        team_dates = elo_df[elo_df["team"] == team]
        past = team_dates[team_dates["date"] < date]
        if past.empty:
            return 1500.0
        return float(past.iloc[-1]["elo"])

    def weighted_form(outcomes: deque, decay: float = 0.9) -> float:
        """Weighted recent form: 1=win, 0.5=draw, 0=loss, decay per older match."""
        pts = [{"home": 1.0, "draw": 0.5, "away": 0.0}.get(o, 0.5) for o in outcomes]
        if not pts:
            return 0.5
        weights = [decay ** i for i in range(len(pts) - 1, -1, -1)]
        return sum(p * w for p, w in zip(pts, weights)) / sum(weights)

    rows = []
    for _, m in df.iterrows():
        home, away = m["home_team"], m["away_team"]
        date = m["date"]
        outcome = m["outcome"]

        # ── features as of kickoff (before this match) ─────────────────────

        elo_h = get_elo_at(home, date)
        elo_a = get_elo_at(away, date)

        form_h = weighted_form(form[home])
        form_a = weighted_form(form[away])

        gf_h = sum(gf[home]) / len(gf[home]) if gf[home] else 1.2
        ga_h = sum(ga[home]) / len(ga[home]) if ga[home] else 1.2
        gf_a = sum(gf[away]) / len(gf[away]) if gf[away] else 1.2
        ga_a = sum(ga[away]) / len(ga[away]) if ga[away] else 1.2

        lp_h = last_played.get(home, None)
        lp_a = last_played.get(away, None)
        rest_h = (pd.Timestamp(date) - pd.Timestamp(lp_h)).days if lp_h else 14
        rest_a = (pd.Timestamp(date) - pd.Timestamp(lp_a)).days if lp_a else 14

        h2h_key = tuple(sorted([home, away]))
        # h2h deque stores the WINNER's name (or 'draw') so rates can be
        # re-oriented to whichever team is home in the current fixture.
        h2h_hist = list(h2h[h2h_key])
        h2h_home_wins = sum(1 for w in h2h_hist if w == home) / max(len(h2h_hist), 1)
        h2h_draws = sum(1 for w in h2h_hist if w == "draw") / max(len(h2h_hist), 1)
        h2h_away_wins = sum(1 for w in h2h_hist if w == away) / max(len(h2h_hist), 1)

        is_neutral = int(m["is_neutral"])
        is_knockout = 1 if m["stage"] == "knockout" else 0

        rows.append({
            "match_id": m["match_id"],
            "date": date,
            "home_team": home,
            "away_team": away,
            "outcome": outcome,
            "elo_home": elo_h,
            "elo_away": elo_a,
            "elo_diff": elo_h - elo_a,
            "form_home": form_h,
            "form_away": form_a,
            "form_diff": form_h - form_a,
            "gf_home": gf_h,
            "ga_home": ga_h,
            "gf_away": gf_a,
            "ga_away": ga_a,
            "rest_home": min(rest_h, 30),
            "rest_away": min(rest_a, 30),
            "rest_diff": min(rest_h, 30) - min(rest_a, 30),
            "is_neutral": is_neutral,
            "is_knockout": is_knockout,
            "h2h_home_win_rate": h2h_home_wins,
            "h2h_draw_rate": h2h_draws,
            "h2h_away_win_rate": h2h_away_wins,
            "h2h_n": len(h2h_hist),
        })

        # ── update windows AFTER recording features ──────────────────────
        home_form_val = outcome  # from home team's perspective
        away_form_val = {"home": "away", "draw": "draw", "away": "home"}[outcome]

        form[home].append(home_form_val)
        form[away].append(away_form_val)
        gf[home].append(m["home_score"])
        ga[home].append(m["away_score"])
        gf[away].append(m["away_score"])
        ga[away].append(m["home_score"])
        last_played[home] = date
        last_played[away] = date

        h2h[h2h_key].append(
            home if outcome == "home" else away if outcome == "away" else "draw"
        )

    feat_df = pd.DataFrame(rows)
    feat_df.to_sql("match_features", conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()
    logger.info("Feature table written: %d rows, %d columns", len(feat_df), len(feat_df.columns))
