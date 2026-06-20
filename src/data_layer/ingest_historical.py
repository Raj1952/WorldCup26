"""
Download and store the martj42 international football results dataset.
~47 000 matches from 1872 to present.  Idempotent — re-running is safe.
"""

from __future__ import annotations

__all__ = ["ingest_historical"]

import hashlib
import sqlite3
import logging
from pathlib import Path

import pandas as pd
import requests

from .team_aliases import resolve_alias
from .validate import derive_outcome

logger = logging.getLogger(__name__)

_HISTORICAL_URLS = [
    "https://raw.githubusercontent.com/martj42/international_results/master/results.csv",
    "https://raw.githubusercontent.com/martj42/international_results/main/results.csv",
    "https://raw.githubusercontent.com/martj42/international-football-results/master/results.csv",
    "https://raw.githubusercontent.com/martj42/international-football-results/main/results.csv",
]
HISTORICAL_URL = _HISTORICAL_URLS[0]
DB_PATH = "data/tempo.db"
RAW_DIR = Path("data/raw")

# Tournaments we treat as "knockout" stage even within named competitions
_KNOCKOUT_KEYWORDS = {"final", "semifinal", "semi-final", "quarter", "third place",
                      "round of 16", "round of 32", "last 16"}

_TOURNAMENT_STAGE_MAP = {
    "FIFA World Cup": "group",
    "Friendly": "friendly",
    "UEFA European Championship": "group",
    "Copa América": "group",
    "Africa Cup of Nations": "group",
}


def _init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            match_id     TEXT PRIMARY KEY,
            date         TEXT NOT NULL,
            home_team    TEXT NOT NULL,
            away_team    TEXT NOT NULL,
            home_score   INTEGER NOT NULL,
            away_score   INTEGER NOT NULL,
            outcome      TEXT NOT NULL,
            tournament   TEXT,
            is_neutral   INTEGER DEFAULT 0,
            stage        TEXT DEFAULT 'group',
            source       TEXT DEFAULT 'historical',
            created_at   TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS ix_matches_date ON matches(date)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_matches_home ON matches(home_team)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_matches_away ON matches(away_team)")
    conn.commit()


def _match_id(date: str, home: str, away: str) -> str:
    raw = f"{date}|{home}|{away}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _infer_stage(tournament: str) -> str:
    t = tournament.lower()
    if "friendly" in t:
        return "friendly"
    for kw in _KNOCKOUT_KEYWORDS:
        if kw in t:
            return "knockout"
    return "group"


def ingest_historical(
    db_path: str = DB_PATH,
    force_download: bool = False,
) -> int:
    """Download historical results, store to SQLite.  Returns rows inserted."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_file = RAW_DIR / "results.csv"

    if not raw_file.exists() or force_download:
        logger.info("Downloading historical results from GitHub …")
        downloaded = False
        for url in _HISTORICAL_URLS:
            try:
                r = requests.get(url, timeout=60)
                r.raise_for_status()
                raw_file.write_bytes(r.content)
                logger.info("Downloaded %d bytes from %s → %s", len(r.content), url, raw_file)
                downloaded = True
                break
            except Exception as exc:
                logger.warning("URL failed (%s): %s", url, exc)
        if not downloaded:
            if not raw_file.exists():
                raise RuntimeError(
                    "Could not download historical data from any source. "
                    "Please manually place results.csv in data/raw/. "
                    "Download from: https://github.com/martj42/international-football-results"
                )
            logger.warning("Using cached file at %s", raw_file)

    df = pd.read_csv(raw_file)
    logger.info("Loaded %d historical rows", len(df))

    # Normalise columns — martj42 schema: date, home_team, away_team,
    # home_score, away_score, tournament, city, country, neutral
    df = df.rename(columns={
        "home_team": "home_raw",
        "away_team": "away_raw",
    })
    df["home_team"] = df["home_raw"].apply(resolve_alias)
    df["away_team"] = df["away_raw"].apply(resolve_alias)
    # Drop rows with no score — martj42 includes future scheduled fixtures with NaN scores;
    # treating them as 0-0 draws corrupts Elo and form features.
    df = df[df["home_score"].notna() & df["away_score"].notna()].copy()
    df["home_score"] = pd.to_numeric(df["home_score"], errors="coerce").astype(int)
    df["away_score"] = pd.to_numeric(df["away_score"], errors="coerce").astype(int)
    df["outcome"] = df.apply(
        lambda r: derive_outcome(r["home_score"], r["away_score"]), axis=1
    )
    df["is_neutral"] = df.get("neutral", False).fillna(False).astype(int)
    df["tournament"] = df.get("tournament", "Friendly").fillna("Friendly")
    df["stage"] = df["tournament"].apply(_infer_stage)
    df["match_id"] = df.apply(
        lambda r: _match_id(str(r["date"]), r["home_team"], r["away_team"]), axis=1
    )
    df["source"] = "historical"

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    _init_db(conn)

    records = df[["match_id", "date", "home_team", "away_team",
                  "home_score", "away_score", "outcome",
                  "tournament", "is_neutral", "stage", "source"]].to_dict("records")

    inserted = 0
    for rec in records:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO matches
                   (match_id,date,home_team,away_team,home_score,away_score,
                    outcome,tournament,is_neutral,stage,source)
                   VALUES (:match_id,:date,:home_team,:away_team,:home_score,
                           :away_score,:outcome,:tournament,:is_neutral,:stage,:source)""",
                rec,
            )
            if conn.execute("SELECT changes()").fetchone()[0]:
                inserted += 1
        except Exception:
            continue

    conn.commit()
    conn.close()
    logger.info("Inserted %d new historical rows into %s", inserted, db_path)
    return inserted
