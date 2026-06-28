"""
Pull live 2026 World Cup fixtures and results.

Primary:  football-data.org REST API (FOOTBALL_DATA_API_KEY in .env)
Fallback: openfootball/world-cup.json on GitHub (no auth)
Manual:   data/manual_results.csv always wins over any feed.

Idempotent — safe to re-run at any time.
"""

from __future__ import annotations

__all__ = ["ingest_live", "resolve_knockout_slots"]

import hashlib
import json
import logging
import os
import re
import sqlite3
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from .team_aliases import resolve_alias
from .validate import derive_outcome

load_dotenv()
logger = logging.getLogger(__name__)

DB_PATH = "data/tempo.db"
MANUAL_CSV = Path("data/manual_results.csv")
RAW_DIR = Path("data/raw")

# openfootball fallback URLs (try in order)
_OFB_URLS = [
    "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json",
    "https://raw.githubusercontent.com/openfootball/worldcup.json/main/2026/worldcup.json",
    "https://raw.githubusercontent.com/openfootball/world-cup/master/2026/worldcup.json",
    "https://raw.githubusercontent.com/openfootball/world-cup/main/2026/worldcup.json",
]

# football-data.org endpoint for WC2026 (competition code WC, season 2026)
_FDORG_BASE = "https://api.football-data.org/v4"
_FDORG_COMPETITION = "WC"
_last_fdorg_call: float = 0.0


def _init_fixtures_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wc2026_fixtures (
            match_id     TEXT PRIMARY KEY,
            date         TEXT NOT NULL,
            kickoff_time TEXT DEFAULT '00:00',
            home_team    TEXT NOT NULL,
            away_team    TEXT NOT NULL,
            group_label  TEXT DEFAULT 'TBD',
            venue        TEXT DEFAULT '',
            city         TEXT DEFAULT '',
            status       TEXT DEFAULT 'scheduled',
            home_score   INTEGER,
            away_score   INTEGER,
            source       TEXT DEFAULT 'openfootball',
            updated_at   TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_fix_date ON wc2026_fixtures(date)"
    )
    conn.commit()


def _fixture_id(date: str, home: str, away: str) -> str:
    raw = f"wc26|{date}|{home}|{away}"
    return "wc26-" + hashlib.md5(raw.encode()).hexdigest()[:8]


def _upsert_fixture(conn: sqlite3.Connection, rec: dict) -> None:
    conn.execute(
        """INSERT INTO wc2026_fixtures
           (match_id,date,kickoff_time,home_team,away_team,group_label,
            venue,city,status,home_score,away_score,source,updated_at)
           VALUES (:match_id,:date,:kickoff_time,:home_team,:away_team,
                   :group_label,:venue,:city,:status,:home_score,:away_score,
                   :source,datetime('now'))
           ON CONFLICT(match_id) DO UPDATE SET
               status=excluded.status,
               home_score=excluded.home_score,
               away_score=excluded.away_score,
               updated_at=excluded.updated_at
        """,
        rec,
    )


def _upsert_result_to_matches(conn: sqlite3.Connection, rec: dict) -> None:
    """Write a completed WC2026 result into the shared matches table."""
    # Remove any stale placeholder row with a different match_id for the same fixture
    # (historical ingest pre-populates future fixtures with 0-0 under a different hash scheme)
    conn.execute(
        "DELETE FROM matches WHERE date=? AND home_team=? AND away_team=? AND match_id!=?",
        (rec["date"], rec["home_team"], rec["away_team"], rec["match_id"]),
    )
    conn.execute(
        """INSERT OR REPLACE INTO matches
           (match_id,date,home_team,away_team,home_score,away_score,
            outcome,tournament,is_neutral,stage,source)
           VALUES (:match_id,:date,:home_team,:away_team,:home_score,:away_score,
                   :outcome,:tournament,:is_neutral,:stage,:source)""",
        rec,
    )


# ── football-data.org ────────────────────────────────────────────────────────

def _fetch_fdorg(api_key: str) -> list[dict]:
    global _last_fdorg_call
    elapsed = time.time() - _last_fdorg_call
    if elapsed < 6.0:
        time.sleep(6.0 - elapsed)
    _last_fdorg_call = time.time()
    headers = {"X-Auth-Token": api_key}
    matches = []
    try:
        url = f"{_FDORG_BASE}/competitions/{_FDORG_COMPETITION}/matches"
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        matches = data.get("matches", [])
        logger.info("football-data.org: fetched %d matches", len(matches))
    except Exception as exc:
        logger.warning("football-data.org failed: %s", exc)
    return matches


def _parse_fdorg(raw_matches: list[dict]) -> list[dict]:
    records = []
    for m in raw_matches:
        try:
            date = m["utcDate"][:10]
            time = m["utcDate"][11:16]
            home = resolve_alias(m["homeTeam"]["name"])
            away = resolve_alias(m["awayTeam"]["name"])
            stage_raw = m.get("stage", "GROUP_STAGE")
            is_group = "GROUP" in stage_raw
            stage = "group" if is_group else "knockout"
            group_label = m.get("group", "").replace("GROUP_", "") or stage_raw[:3]
            score = m.get("score", {})
            ft = score.get("fullTime", {})
            h_score = ft.get("home")
            a_score = ft.get("away")
            status_raw = m.get("status", "SCHEDULED")
            status = "played" if status_raw == "FINISHED" else "scheduled"
            mid = _fixture_id(date, home, away)
            records.append({
                "match_id": mid,
                "date": date,
                "kickoff_time": time,
                "home_team": home,
                "away_team": away,
                "group_label": group_label,
                "venue": m.get("venue", ""),
                "city": "",
                "status": status,
                "home_score": h_score,
                "away_score": a_score,
                "source": "football-data.org",
            })
        except Exception:
            continue
    return records


# ── openfootball JSON fallback ───────────────────────────────────────────────

def _parse_group_label(group_str: str, round_str: str) -> str:
    """Derive a short group/stage label from openfootball group or round fields."""
    g = (group_str or "").strip()
    if g.startswith("Group "):
        return g.replace("Group ", "")[:1]
    r = (round_str or "").lower()
    if "round of 32" in r:
        return "R32"
    if "round of 16" in r:
        return "R16"
    if "quarter" in r:
        return "QF"
    if "semi" in r:
        return "SF"
    if "third" in r or "3rd" in r:
        return "3P"
    if "final" in r:
        return "Final"
    return "GRP"


def _parse_time(raw_time: str) -> str:
    """Extract HH:MM from strings like '13:00 UTC-6'."""
    if not raw_time:
        return "00:00"
    return raw_time.split()[0][:5]


def _fetch_openfootball() -> list[dict]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cached = RAW_DIR / "wc2026_openfootball.json"

    raw = None
    for url in _OFB_URLS:
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                raw = r.json()
                cached.write_bytes(r.content)
                logger.info("openfootball: fetched from %s", url)
                break
        except Exception as exc:
            logger.debug("openfootball URL %s failed: %s", url, exc)

    if raw is None and cached.exists():
        logger.warning("openfootball: using cached file %s", cached)
        raw = json.loads(cached.read_text(encoding="utf-8"))

    if raw is None:
        logger.warning("openfootball: no data available")
        return []

    # The openfootball worldcup.json 2026 uses a flat "matches" array
    # with string team names and "score": {"ft": [h, a]} for results.
    matches_list = raw.get("matches", [])
    if not matches_list:
        logger.warning("openfootball: unexpected JSON structure — no 'matches' key")
        return []

    records = []
    for match in matches_list:
        try:
            date = match.get("date", "")
            if not date:
                continue
            raw_time = match.get("time", "")
            kickoff = _parse_time(raw_time)

            team1 = resolve_alias(str(match.get("team1", "")))
            team2 = resolve_alias(str(match.get("team2", "")))
            if not team1 or not team2:
                continue

            group_label = _parse_group_label(
                match.get("group", ""),
                match.get("round", ""),
            )

            score = match.get("score", {})
            ft = score.get("ft") if isinstance(score, dict) else None
            if ft and len(ft) == 2:
                h_score, a_score = int(ft[0]), int(ft[1])
                status = "played"
            else:
                h_score, a_score = None, None
                status = "scheduled"

            venue = str(match.get("ground", match.get("stadium", "")))
            mid = _fixture_id(date, team1, team2)

            records.append({
                "match_id": mid,
                "date": date,
                "kickoff_time": kickoff,
                "home_team": team1,
                "away_team": team2,
                "group_label": group_label,
                "venue": venue,
                "city": "",
                "status": status,
                "home_score": h_score,
                "away_score": a_score,
                "source": "openfootball",
            })
        except Exception as exc:
            logger.debug("openfootball parse error on match: %s — %s", match, exc)
            continue

    logger.info("openfootball: parsed %d fixtures", len(records))
    return records


# ── manual override ──────────────────────────────────────────────────────────

def _load_manual() -> list[dict]:
    if not MANUAL_CSV.exists():
        return []
    df = pd.read_csv(MANUAL_CSV)
    if df.empty:
        return []
    records = []
    for _, row in df.iterrows():
        try:
            mid = str(row.get("match_id", "")).strip() or _fixture_id(
                str(row["date"]),
                resolve_alias(str(row["home_team"])),
                resolve_alias(str(row["away_team"])),
            )
            records.append({
                "match_id": mid,
                "date": str(row["date"]),
                "kickoff_time": "00:00",
                "home_team": resolve_alias(str(row["home_team"])),
                "away_team": resolve_alias(str(row["away_team"])),
                "group_label": "MAN",
                "venue": "",
                "city": "",
                "status": "played",
                "home_score": int(row["home_score"]),
                "away_score": int(row["away_score"]),
                "source": "manual",
            })
        except Exception:
            continue
    logger.info("Loaded %d manual overrides", len(records))
    return records


# ── knockout slot resolution ─────────────────────────────────────────────────

_IS_SLOT_CODE = re.compile(r"^[0-9]|^[WL]\d+$|/")

# Match number at which each knockout round starts
_ROUND_START = {"R32": 73, "R16": 89, "QF": 97, "SF": 101}


def _concrete_score(name: str) -> int:
    """0 if name is a slot/placeholder code; 1 if it's a real team name."""
    return 0 if _IS_SLOT_CODE.match(str(name)) else 1


def resolve_knockout_slots(
    conn: sqlite3.Connection,
    manual_results_path: str = "data/manual_results.csv",
) -> None:
    """
    Resolve W- and L-slot codes in knockout fixtures using real match results.

    The i-th fixture (0-indexed, chronological) within each round maps to
    match number ROUND_START + i.  Winner → W{n}, loser → L{n}.

    Penalty draws: 90-min draw with no winner yet; if data/manual_results.csv
    has a `knockout_winner` column for that match, that team advances.
    Without it the slot stays unresolved (safe to call repeatedly).
    """
    # Load manual penalty winners: (date, home, away) → winning team
    manual_winners: dict[tuple, str] = {}
    mp = Path(manual_results_path)
    if mp.exists():
        try:
            df_man = pd.read_csv(mp)
            if "knockout_winner" in df_man.columns:
                for _, r in df_man[df_man["knockout_winner"].notna()].iterrows():
                    key = (
                        str(r["date"]),
                        resolve_alias(str(r["home_team"])),
                        resolve_alias(str(r["away_team"])),
                    )
                    manual_winners[key] = resolve_alias(str(r["knockout_winner"]))
        except Exception:
            pass

    for round_key, start in _ROUND_START.items():
        df_round = pd.read_sql(
            "SELECT match_id, date, kickoff_time, home_team, away_team, "
            "       home_score, away_score "
            "FROM wc2026_fixtures WHERE group_label=? "
            "ORDER BY date ASC, kickoff_time ASC",
            conn,
            params=(round_key,),
        )
        if df_round.empty:
            continue

        # Deduplicate duplicate rows for the same timeslot: prefer most concrete
        df_round["_conc"] = df_round.apply(
            lambda r: _concrete_score(r["home_team"]) + _concrete_score(r["away_team"]),
            axis=1,
        )
        df_round = (
            df_round
            .sort_values(["date", "kickoff_time", "_conc"], ascending=[True, True, False])
            .groupby(["date", "kickoff_time"], sort=False)
            .first()
            .reset_index()
            .sort_values(["date", "kickoff_time"])
            .reset_index(drop=True)
        )

        for i, row in df_round.iterrows():
            match_num = start + i
            home = str(row["home_team"])
            away = str(row["away_team"])
            h_score = row["home_score"]
            a_score = row["away_score"]

            if pd.isna(h_score) or pd.isna(a_score):
                continue  # match not played yet

            h_score, a_score = int(h_score), int(a_score)

            if h_score > a_score:
                winner, loser = home, away
            elif a_score > h_score:
                winner, loser = away, home
            else:
                # 90-min draw — check manual penalty winner
                key = (str(row["date"]), home, away)
                winner = manual_winners.get(key)
                if winner is None:
                    continue  # unresolved penalty
                loser = away if winner == home else home

            w_code = f"W{match_num}"
            l_code = f"L{match_num}"
            conn.execute(
                "UPDATE wc2026_fixtures SET home_team=? WHERE home_team=?", (winner, w_code)
            )
            conn.execute(
                "UPDATE wc2026_fixtures SET away_team=? WHERE away_team=?", (winner, w_code)
            )
            conn.execute(
                "UPDATE wc2026_fixtures SET home_team=? WHERE home_team=?", (loser, l_code)
            )
            conn.execute(
                "UPDATE wc2026_fixtures SET away_team=? WHERE away_team=?", (loser, l_code)
            )

    conn.commit()
    logger.info("Knockout slot resolution complete.")


# ── main entry point ─────────────────────────────────────────────────────────

def ingest_live(db_path: str = DB_PATH) -> int:
    """Fetch WC2026 fixtures/results, store to SQLite.  Returns fixtures upserted."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    _init_fixtures_table(conn)

    # Ensure matches table exists (may not if historical wasn't run)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            match_id TEXT PRIMARY KEY, date TEXT, home_team TEXT, away_team TEXT,
            home_score INTEGER, away_score INTEGER, outcome TEXT,
            tournament TEXT, is_neutral INTEGER DEFAULT 0,
            stage TEXT DEFAULT 'group', source TEXT DEFAULT 'live',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()

    # Collect fixture records from all sources (later sources override earlier ones)
    all_records: dict[str, dict] = {}

    # 1. openfootball (no key needed)
    for rec in _fetch_openfootball():
        all_records[rec["match_id"]] = rec

    # 2. football-data.org (richer, if key available)
    api_key = os.getenv("FOOTBALL_DATA_API_KEY", "")
    if api_key:
        for rec in _parse_fdorg(_fetch_fdorg(api_key)):
            all_records[rec["match_id"]] = rec

    # 3. manual overrides always win
    for rec in _load_manual():
        all_records[rec["match_id"]] = rec

    upserted = 0
    for rec in all_records.values():
        try:
            _upsert_fixture(conn, rec)
            upserted += 1
            # If played, also write to matches table for training
            if rec["status"] == "played" and rec["home_score"] is not None:
                h, a = int(rec["home_score"]), int(rec["away_score"])
                match_rec = {
                    "match_id": rec["match_id"],
                    "date": rec["date"],
                    "home_team": rec["home_team"],
                    "away_team": rec["away_team"],
                    "home_score": h,
                    "away_score": a,
                    "outcome": derive_outcome(h, a),
                    "tournament": "FIFA World Cup 2026",
                    "is_neutral": 1,
                    "stage": "group" if rec["group_label"] in list("ABCDEFGHIJKL") else "knockout",
                    "source": rec["source"],
                }
                _upsert_result_to_matches(conn, match_rec)
        except Exception as exc:
            logger.debug("upsert failed for %s: %s", rec.get("match_id"), exc)

    conn.commit()

    # Resolve W/L slot codes for any knockout rounds where results are in
    resolve_knockout_slots(conn, manual_results_path=str(MANUAL_CSV))

    conn.close()
    logger.info("Upserted %d WC2026 fixtures", upserted)
    return upserted
