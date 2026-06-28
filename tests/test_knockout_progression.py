"""
Integration test: knockout slot progression R32 → Final.

Covers:
  - Fix 3: _SLOT_RE correctly flags W73-W88 (2-digit W-codes)
  - Fix 1: resolve_knockout_slots() propagates real team names after results
  - Fix 2: unresolved penalty draws stay as slot codes (safe to re-run)
  - Fix 5: 90-min draw → draw Elo update, not penalty winner (documented)
  - Fix 6: _tournament_complete() reads Final fixture result
"""
import sqlite3

import pandas as pd
import pytest

from src.data_layer.ingest_live import _fixture_id, resolve_knockout_slots
from src.intelligence_layer.predict import _is_concrete_team


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_db(path: str) -> None:
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE wc2026_fixtures (
            match_id     TEXT PRIMARY KEY,
            date         TEXT NOT NULL,
            kickoff_time TEXT DEFAULT '00:00',
            home_team    TEXT NOT NULL,
            away_team    TEXT NOT NULL,
            group_label  TEXT DEFAULT 'TBD',
            home_score   INTEGER,
            away_score   INTEGER,
            status       TEXT DEFAULT 'scheduled',
            source       TEXT DEFAULT 'test'
        )
    """)
    conn.commit()
    conn.close()


def _insert(
    db: str, date: str, kickoff: str, home: str, away: str, group: str,
    h=None, a=None,
) -> str:
    mid = _fixture_id(date, home, away)
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT OR REPLACE INTO wc2026_fixtures "
        "(match_id,date,kickoff_time,home_team,away_team,group_label,home_score,away_score) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (mid, date, kickoff, home, away, group, h, a),
    )
    conn.commit()
    conn.close()
    return mid


def _home_team(db: str, group: str) -> str:
    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT home_team FROM wc2026_fixtures WHERE group_label=?", (group,)
    ).fetchone()
    conn.close()
    return row[0] if row else ""


# ── Fix 3: _SLOT_RE ───────────────────────────────────────────────────────────


class TestIsConcreteTeam:
    def test_real_team_is_concrete(self):
        assert _is_concrete_team("Brazil") is True

    def test_w_code_two_digits_not_concrete(self):
        # W73–W88 were previously not caught by old regex (^[A-Z]\d{3,}$)
        assert _is_concrete_team("W73") is False

    def test_w_code_three_digits_not_concrete(self):
        assert _is_concrete_team("W101") is False

    def test_l_code_not_concrete(self):
        assert _is_concrete_team("L101") is False

    def test_group_slot_not_concrete(self):
        assert _is_concrete_team("1A") is False

    def test_concrete_team_with_spaces(self):
        assert _is_concrete_team("South Africa") is True


# ── Fix 1: resolve_knockout_slots ─────────────────────────────────────────────


class TestResolveKnockoutSlots:
    def test_home_winner_w_code_resolved(self, tmp_path):
        """Home win → W73 becomes home team in R16 fixture."""
        db = str(tmp_path / "t.db")
        _make_db(db)
        _insert(db, "2026-06-28", "12:00", "Brazil", "Japan", "R32", 2, 0)
        _insert(db, "2026-07-04", "12:00", "W73", "W74", "R16")

        conn = sqlite3.connect(db)
        resolve_knockout_slots(conn)
        conn.close()

        assert _home_team(db, "R16") == "Brazil"

    def test_away_winner_w_code_resolved(self, tmp_path):
        """Away win → W73 becomes away team (Japan) in R16 fixture."""
        db = str(tmp_path / "t.db")
        _make_db(db)
        _insert(db, "2026-06-28", "12:00", "Brazil", "Japan", "R32", 0, 2)
        _insert(db, "2026-07-04", "12:00", "W73", "W74", "R16")

        conn = sqlite3.connect(db)
        resolve_knockout_slots(conn)
        conn.close()

        assert _home_team(db, "R16") == "Japan"

    def test_draw_without_manual_not_resolved(self, tmp_path):
        """90-min draw + no manual file → slot stays as W-code (safe)."""
        db = str(tmp_path / "t.db")
        _make_db(db)
        _insert(db, "2026-06-28", "12:00", "Brazil", "Japan", "R32", 1, 1)
        _insert(db, "2026-07-04", "12:00", "W73", "W74", "R16")

        conn = sqlite3.connect(db)
        resolve_knockout_slots(conn, manual_results_path=str(tmp_path / "no_file.csv"))
        conn.close()

        assert _home_team(db, "R16") == "W73"  # unchanged

    def test_draw_with_manual_penalty_winner(self, tmp_path):
        """90-min draw + manual knockout_winner → slot resolved to penalty winner."""
        db = str(tmp_path / "t.db")
        _make_db(db)
        _insert(db, "2026-06-28", "12:00", "Brazil", "Japan", "R32", 1, 1)
        _insert(db, "2026-07-04", "12:00", "W73", "W74", "R16")

        manual = tmp_path / "manual_results.csv"
        manual.write_text(
            "date,home_team,away_team,home_score,away_score,knockout_winner\n"
            "2026-06-28,Brazil,Japan,1,1,Japan\n"
        )

        conn = sqlite3.connect(db)
        resolve_knockout_slots(conn, manual_results_path=str(manual))
        conn.close()

        assert _home_team(db, "R16") == "Japan"

    def test_l_code_resolved_for_3p_match(self, tmp_path):
        """Loser of SF match 101 (Argentina) replaces L101 in 3P fixture."""
        db = str(tmp_path / "t.db")
        _make_db(db)
        # SF: Brazil beats Argentina → W101=Brazil, L101=Argentina
        _insert(db, "2026-07-14", "20:00", "Brazil", "Argentina", "SF", 2, 1)
        _insert(db, "2026-07-18", "20:00", "L101", "L102", "3P")

        conn = sqlite3.connect(db)
        resolve_knockout_slots(conn)
        conn.close()

        assert _home_team(db, "3P") == "Argentina"

    def test_unplayed_match_slot_unchanged(self, tmp_path):
        """Unplayed R32 match → downstream W-code stays as-is."""
        db = str(tmp_path / "t.db")
        _make_db(db)
        _insert(db, "2026-06-28", "12:00", "Brazil", "Japan", "R32")  # no scores
        _insert(db, "2026-07-04", "12:00", "W73", "W74", "R16")

        conn = sqlite3.connect(db)
        resolve_knockout_slots(conn)
        conn.close()

        assert _home_team(db, "R16") == "W73"

    def test_idempotent_double_call(self, tmp_path):
        """Calling resolve twice produces the same result as calling once."""
        db = str(tmp_path / "t.db")
        _make_db(db)
        _insert(db, "2026-06-28", "12:00", "Brazil", "Japan", "R32", 3, 0)
        _insert(db, "2026-07-04", "12:00", "W73", "W74", "R16")

        conn = sqlite3.connect(db)
        resolve_knockout_slots(conn)
        resolve_knockout_slots(conn)  # second call — should be safe
        conn.close()

        assert _home_team(db, "R16") == "Brazil"

    def test_winner_propagates_to_final(self, tmp_path):
        """SF winner W-code is replaced in the Final fixture."""
        db = str(tmp_path / "t.db")
        _make_db(db)
        _insert(db, "2026-07-14", "20:00", "Brazil", "Argentina", "SF", 2, 1)
        _insert(db, "2026-07-15", "20:00", "France", "Spain", "SF", 1, 0)
        _insert(db, "2026-07-19", "20:00", "W101", "W102", "Final")

        conn = sqlite3.connect(db)
        resolve_knockout_slots(conn)
        conn.close()

        assert _home_team(db, "Final") == "Brazil"


# ── Fix 6: tournament complete ────────────────────────────────────────────────


class TestTournamentComplete:
    def test_not_complete_when_final_unplayed(self, tmp_path):
        db = str(tmp_path / "t.db")
        _make_db(db)
        _insert(db, "2026-07-19", "20:00", "Brazil", "France", "Final")

        from src.presentation_layer.pages.today import _tournament_complete
        assert _tournament_complete(db_path=db) is False

    def test_complete_when_final_has_result(self, tmp_path):
        db = str(tmp_path / "t.db")
        _make_db(db)
        _insert(db, "2026-07-19", "20:00", "Brazil", "France", "Final", 2, 1)

        from src.presentation_layer.pages.today import _tournament_complete
        assert _tournament_complete(db_path=db) is True

    def test_not_complete_with_empty_db(self, tmp_path):
        db = str(tmp_path / "t.db")
        _make_db(db)

        from src.presentation_layer.pages.today import _tournament_complete
        assert _tournament_complete(db_path=db) is False
