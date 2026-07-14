"""
Training/serving parity guard.

The features served at prediction time (features.get_prediction_features)
must be numerically identical to what build_features would compute for the
same fixture. This is verified by appending the fixture to the matches table
with a dummy result, re-running build_features, and comparing the final row.
"""

import sqlite3

import numpy as np
import pytest

from src.data_layer.build_features import build_features
from src.intelligence_layer.features import get_prediction_features, FEATURE_COLS

TEAMS = ["Ayland", "Beeland", "Ceeland", "Deeland", "Eeland"]


def _make_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE matches (
            match_id TEXT PRIMARY KEY, date TEXT, home_team TEXT, away_team TEXT,
            home_score INTEGER, away_score INTEGER, outcome TEXT,
            tournament TEXT, is_neutral INTEGER DEFAULT 0,
            stage TEXT DEFAULT 'group', source TEXT DEFAULT 'test'
        )
    """)
    # Deterministic synthetic history: round-robin repeated over months
    rng = np.random.default_rng(7)
    rows, day = [], 0
    for rnd in range(12):
        for i in range(len(TEAMS)):
            for j in range(i + 1, len(TEAMS)):
                home, away = (TEAMS[i], TEAMS[j]) if (rnd + i) % 2 == 0 else (TEAMS[j], TEAMS[i])
                hs, as_ = int(rng.integers(0, 4)), int(rng.integers(0, 4))
                outcome = "home" if hs > as_ else "away" if as_ > hs else "draw"
                date = f"2024-{1 + day // 28:02d}-{1 + day % 28:02d}"
                rows.append((f"m{rnd}-{i}-{j}", date, home, away, hs, as_,
                             outcome, "Test Cup", 0, "group", "test"))
                day += 1
    conn.executemany(
        "INSERT INTO matches VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows
    )
    conn.commit()
    conn.close()


def _append_fixture(db_path: str, home: str, away: str, date: str,
                    is_neutral: int, stage: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO matches VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("future-1", date, home, away, 1, 0, "home", "Test Cup",
         is_neutral, stage, "test"),
    )
    conn.commit()
    conn.close()


@pytest.mark.parametrize("home,away", [("Ayland", "Beeland"), ("Deeland", "Ceeland")])
def test_serving_features_match_training_features(tmp_path, home, away):
    db = str(tmp_path / "parity.db")
    _make_db(db)
    build_features(db_path=db)

    date = "2024-12-01"   # after all synthetic history
    served = get_prediction_features(
        home_team=home, away_team=away, date=date,
        is_neutral=True, is_knockout=True, db_path=db,
    )
    assert served is not None, "serving path returned no features"

    # Ground truth: append the fixture with a dummy result and let the
    # training pipeline compute its pre-match features.
    _append_fixture(db, home, away, date, is_neutral=1, stage="knockout")
    build_features(db_path=db)

    conn = sqlite3.connect(db)
    row = conn.execute(
        f"SELECT {','.join(FEATURE_COLS)} FROM match_features "
        "WHERE match_id='future-1'"
    ).fetchone()
    conn.close()
    trained = np.array(row, dtype=np.float32)

    mismatches = [
        f"{col}: served={s:.5f} trained={t:.5f}"
        for col, s, t in zip(FEATURE_COLS, served[0], trained)
        if not np.isclose(s, t, atol=1e-4)
    ]
    assert not mismatches, "training/serving feature skew:\n" + "\n".join(mismatches)


def test_h2h_is_oriented_to_current_home_team(tmp_path):
    """Team A beat B in every past meeting → h2h_home_win_rate must flip
    with fixture orientation (this was the C2 bug)."""
    db = str(tmp_path / "h2h.db")
    conn = sqlite3.connect(db)
    conn.execute("""
        CREATE TABLE matches (
            match_id TEXT PRIMARY KEY, date TEXT, home_team TEXT, away_team TEXT,
            home_score INTEGER, away_score INTEGER, outcome TEXT,
            tournament TEXT, is_neutral INTEGER DEFAULT 0,
            stage TEXT DEFAULT 'group', source TEXT DEFAULT 'test'
        )
    """)
    rows = []
    for k in range(6):   # Ayland always wins, alternating venue
        home, away = ("Ayland", "Beeland") if k % 2 == 0 else ("Beeland", "Ayland")
        hs, as_ = (2, 0) if home == "Ayland" else (0, 2)
        outcome = "home" if hs > as_ else "away"
        rows.append((f"h{k}", f"2024-01-{k+1:02d}", home, away, hs, as_,
                     outcome, "Test Cup", 0, "group", "test"))
    conn.executemany("INSERT INTO matches VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()
    build_features(db_path=db)

    i_hw = FEATURE_COLS.index("h2h_home_win_rate")
    i_aw = FEATURE_COLS.index("h2h_away_win_rate")

    x1 = get_prediction_features("Ayland", "Beeland", "2024-02-01",
                                 is_neutral=True, is_knockout=False, db_path=db)
    x2 = get_prediction_features("Beeland", "Ayland", "2024-02-01",
                                 is_neutral=True, is_knockout=False, db_path=db)
    assert x1[0, i_hw] == 1.0 and x1[0, i_aw] == 0.0
    assert x2[0, i_hw] == 0.0 and x2[0, i_aw] == 1.0
