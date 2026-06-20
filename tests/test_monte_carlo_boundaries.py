"""
Hard-edge boundary tests for Monte Carlo group-stage conditioning.

Constructs fully-synthetic standings with no remaining matches so that every
one of the 50,000 sims produces the same deterministic ranking.  This makes
the boundary assertions exact (0 / 50,000 counts) rather than probabilistic.

Two boundaries under test:

  CLINCHED — SynthA1 won all three group-stage matches, sits 1st in Group A
  with 9 pts / +6 GD, and all matches are played.  No remaining match can
  change its rank.  Asserts r32_pct == 1.0 exactly.

  ELIMINATED — SynthA4 lost all three group-stage matches, sits 4th in
  Group A with 0 pts / −5 GD, and all matches are played.  It cannot appear
  in the third-place pool (the best-8 competition pulls only the 3rd-place
  team per group, never the 4th-place team).  Asserts r32_pct == 0.0 exactly.

Why this demonstrates real conditioning, not a trivial no-op:
  A buggy simulator could fail either assertion by:
  - Starting from wrong initial standings (wrong pts/GD → incorrect rank)
  - A tiebreak scoring error that promotes SynthA4 above SynthA3
  - A best-8 indexing bug that counts a 4th-place team as a "third"
  All three failure modes are caught by the exact 0.0 / 1.0 check.
"""

import pandas as pd
import pytest

from src.intelligence_layer.monte_carlo import simulate_group_stage, SEED, N_SIMS

GROUPS = list("ABCDEFGHIJKL")


# ── Middle-case data builder ───────────────────────────────────────────────────

def _played_group_b_to_i(group: str, t1: str, t2: str, t3: str, t4: str) -> list[dict]:
    """
    Six fully-played matches giving t3 exactly 3 pts / GD=0.

    Results:  t1 vs t2 → 2-0,  t3 vs t4 → 2-0,
              t1 vs t3 → 1-0,  t2 vs t4 → 2-0,
              t2 vs t3 → 1-0,  t1 vs t4 → 2-0

    t3 final: W1 D0 L2, GF=2, GA=2, GD=0, pts=3  (verified by hand)
    """
    return [
        {"date": "2026-06-11", "group_label": group,
         "home_team": t1, "away_team": t2, "home_score": 2, "away_score": 0},
        {"date": "2026-06-11", "group_label": group,
         "home_team": t3, "away_team": t4, "home_score": 2, "away_score": 0},
        {"date": "2026-06-14", "group_label": group,
         "home_team": t1, "away_team": t3, "home_score": 1, "away_score": 0},
        {"date": "2026-06-14", "group_label": group,
         "home_team": t2, "away_team": t4, "home_score": 2, "away_score": 0},
        {"date": "2026-06-17", "group_label": group,
         "home_team": t2, "away_team": t3, "home_score": 1, "away_score": 0},
        {"date": "2026-06-17", "group_label": group,
         "home_team": t1, "away_team": t4, "home_score": 2, "away_score": 0},
    ]


def _played_group_j_to_l(group: str, t1: str, t2: str, t3: str, t4: str) -> list[dict]:
    """
    Six fully-played matches giving t3 exactly 3 pts / GD=−4.

    Results:  t1 vs t2 → 2-0,  t3 vs t4 → 1-0,
              t1 vs t3 → 2-0,  t2 vs t4 → 2-0,
              t2 vs t3 → 3-0,  t1 vs t4 → 2-0

    t3 final: W1 D0 L2, GF=1, GA=5, GD=−4, pts=3  (verified by hand)
    """
    return [
        {"date": "2026-06-11", "group_label": group,
         "home_team": t1, "away_team": t2, "home_score": 2, "away_score": 0},
        {"date": "2026-06-11", "group_label": group,
         "home_team": t3, "away_team": t4, "home_score": 1, "away_score": 0},
        {"date": "2026-06-14", "group_label": group,
         "home_team": t1, "away_team": t3, "home_score": 2, "away_score": 0},
        {"date": "2026-06-14", "group_label": group,
         "home_team": t2, "away_team": t4, "home_score": 2, "away_score": 0},
        {"date": "2026-06-17", "group_label": group,
         "home_team": t2, "away_team": t3, "home_score": 3, "away_score": 0},
        {"date": "2026-06-17", "group_label": group,
         "home_team": t1, "away_team": t4, "home_score": 2, "away_score": 0},
    ]


def _build_middle_case_data() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Construct 12 groups where Group A has ONE remaining match (SynthA3 vs SynthA4)
    and the threshold for best-8 thirds qualification is calibrated so that:

      SynthA3 wins  (p=0.40) → 6 pts → qualifies (always best-third or top-2)
      SynthA3 draws (p=0.30) → 4 pts → qualifies (4 pts beats all 3-pt thirds)
      SynthA3 loses (p=0.30) → stays 3 pts, becomes 4th in group → does NOT qualify

    Global third-place threshold:
      Groups B-I  (8 groups): 3rd-place at 3 pts / GD=0    (score 3_000_002)
      Groups J-L  (3 groups): 3rd-place at 3 pts / GD=−4   (score 2_996_001)
      SynthA3 after loss:     3 pts / GD ≤ −3              (score ≤ 2_997_001)
        → 9th-best third (8 B-I thirds ahead) → no advancement

    Expected P(SynthA3 R32) = P(win) + P(draw) = 0.40 + 0.30 = 0.70
    """
    all_played: list[dict] = []
    team_group: dict[str, str] = {}

    # ── Group A: partially played (MD1+MD2 done, MD3 remaining) ─────────────
    a1, a2, a3, a4 = "SynthA1", "SynthA2", "SynthA3", "SynthA4"
    for t in (a1, a2, a3, a4):
        team_group[t] = "A"
    all_played += [
        # MD1
        {"date": "2026-06-11", "group_label": "A",
         "home_team": a1, "away_team": a2, "home_score": 2, "away_score": 0},
        {"date": "2026-06-11", "group_label": "A",
         "home_team": a3, "away_team": a4, "home_score": 1, "away_score": 0},
        # MD2  (A1 beats A3 3-0 → A3 GD drops to −2)
        {"date": "2026-06-14", "group_label": "A",
         "home_team": a1, "away_team": a3, "home_score": 3, "away_score": 0},
        {"date": "2026-06-14", "group_label": "A",
         "home_team": a2, "away_team": a4, "home_score": 2, "away_score": 0},
    ]
    # After MD1+MD2:
    #   SynthA1: 6 pts / GF=5, GA=0, GD=+5
    #   SynthA2: 3 pts / GF=2, GA=2, GD=0
    #   SynthA3: 3 pts / GF=1, GA=3, GD=−2   ← the team under test
    #   SynthA4: 0 pts / GF=0, GA=3, GD=−3

    # ── Groups B-I: fully played, third-place at GD=0 ────────────────────────
    for grp in list("BCDEFGHI"):
        t1, t2, t3, t4 = (f"Synth{grp}{i}" for i in range(1, 5))
        for t in (t1, t2, t3, t4):
            team_group[t] = grp
        all_played += _played_group_b_to_i(grp, t1, t2, t3, t4)

    # ── Groups J-L: fully played, third-place at GD=−4 ───────────────────────
    for grp in list("JKL"):
        t1, t2, t3, t4 = (f"Synth{grp}{i}" for i in range(1, 5))
        for t in (t1, t2, t3, t4):
            team_group[t] = grp
        all_played += _played_group_j_to_l(grp, t1, t2, t3, t4)

    played_df = pd.DataFrame(all_played)

    # ── Remaining matches: only Group A MD3 ──────────────────────────────────
    remaining_df = pd.DataFrame([
        # SynthA1 vs SynthA2 — needed so the group resolves correctly
        {"date": "2026-06-17", "group_label": "A",
         "home_team": a1, "away_team": a2,
         "p_home": 0.60, "p_draw": 0.20, "p_away": 0.20},
        # SynthA3 vs SynthA4 — the key stochastic match
        {"date": "2026-06-17", "group_label": "A",
         "home_team": a3, "away_team": a4,
         "p_home": 0.40, "p_draw": 0.30, "p_away": 0.30},
    ])

    return played_df, remaining_df, team_group

# ── Synthetic match builder ────────────────────────────────────────────────────

def _played_group(group: str, t1: str, t2: str, t3: str, t4: str) -> list[dict]:
    """
    Six fully-played matches for a 4-team group with deterministic outcomes.

    Match schedule and results
    --------------------------
    Matchday 1:  t1 vs t2  → 2-0   |   t3 vs t4  → 1-0
    Matchday 2:  t1 vs t3  → 2-0   |   t2 vs t4  → 2-0
    Matchday 3:  t2 vs t3  → 1-0   |   t1 vs t4  → 2-0

    Final standings (verified by hand)
    -----------------------------------
    t1: W3  D0  L0  GF=6  GA=0  GD=+6  pts=9   → 1st
    t2: W2  D0  L1  GF=3  GA=2  GD=+1  pts=6   → 2nd
    t3: W1  D0  L2  GF=1  GA=3  GD=−2  pts=3   → 3rd
    t4: W0  D0  L3  GF=0  GA=5  GD=−5  pts=0   → 4th

    Ranking tiebreak scores (pts×1e6 + GD×1e3 + GF):
      t1: 9_006_006   t2: 6_001_003   t3: 2_998_001   t4: −5_000
    No ties exist, so the ranking is deterministic in all 50k sims.
    """
    return [
        # Matchday 1
        {"date": "2026-06-11", "group_label": group,
         "home_team": t1, "away_team": t2, "home_score": 2, "away_score": 0},
        {"date": "2026-06-11", "group_label": group,
         "home_team": t3, "away_team": t4, "home_score": 1, "away_score": 0},
        # Matchday 2
        {"date": "2026-06-14", "group_label": group,
         "home_team": t1, "away_team": t3, "home_score": 2, "away_score": 0},
        {"date": "2026-06-14", "group_label": group,
         "home_team": t2, "away_team": t4, "home_score": 2, "away_score": 0},
        # Matchday 3
        {"date": "2026-06-17", "group_label": group,
         "home_team": t2, "away_team": t3, "home_score": 1, "away_score": 0},
        {"date": "2026-06-17", "group_label": group,
         "home_team": t1, "away_team": t4, "home_score": 2, "away_score": 0},
    ]


def _build_synthetic_data() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    12 fully-played groups (A–L), no remaining matches.
    Each group uses the same deterministic pattern above with team names
    SynthX1 … SynthX4 where X is the group letter.
    """
    all_played: list[dict] = []
    team_group: dict[str, str] = {}

    for group in GROUPS:
        t1, t2, t3, t4 = (f"Synth{group}{i}" for i in range(1, 5))
        all_played.extend(_played_group(group, t1, t2, t3, t4))
        for team in (t1, t2, t3, t4):
            team_group[team] = group

    played_df = pd.DataFrame(all_played)

    # Empty remaining — every group is fully resolved, nothing left to simulate.
    remaining_df = pd.DataFrame(
        columns=["date", "group_label", "home_team", "away_team",
                 "p_home", "p_draw", "p_away"]
    )

    return played_df, remaining_df, team_group


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestMonteCarloHardBoundaries:
    """Exact 0 % / 100 % boundary checks on deterministic synthetic standings."""

    def setup_method(self):
        played, remaining, team_group = _build_synthetic_data()
        self.results, self.group_teams = simulate_group_stage(
            played, remaining, team_group, n_sims=N_SIMS, seed=SEED
        )

    # ── CLINCHED ─────────────────────────────────────────────────────────────

    def test_clinched_team_is_exactly_100_pct(self):
        """
        SynthA1: 9 pts / GD +6 / 1st in Group A, all matches played.

        Conditioning proof: the simulator must read the real played results
        (GF=6, GA=0 from the three 2-0 wins), apply pts=9, and rank SynthA1
        above every other Group A team in every single sim.  A wrong initial
        standing (e.g. starting from 0 pts instead of 9) would rank it
        incorrectly and break this assertion.
        """
        r = self.results["SynthA1"]
        assert r["r32_count"] == N_SIMS, (
            f"Expected {N_SIMS} / {N_SIMS} sims advancing but got {r['r32_count']}"
        )
        assert r["r32_pct"] == 1.0, (
            f"SynthA1 R32 = {r['r32_pct']:.6%} — should be exactly 100.000000%"
        )

    def test_clinched_team_qualifies_via_top2_not_third(self):
        """SynthA1 is 1st — it should never need the best-third route."""
        r = self.results["SynthA1"]
        assert r["r32_top2_count"] == N_SIMS
        assert r["r32_third_count"] == 0

    # ── ELIMINATED ───────────────────────────────────────────────────────────

    def test_eliminated_team_is_exactly_0_pct(self):
        """
        SynthA4: 0 pts / GD −5 / 4th in Group A, all matches played.

        Key conditioning proof: the simulator must place SynthA4 in rank-4
        (below SynthA3 which has 3 pts) in every sim, so SynthA4 is never
        entered into the best-8 third-place competition.  A tiebreak bug
        that confused 3rd and 4th, or a best-8 indexing bug that picked the
        4th-place team instead of the 3rd, would surface here.
        """
        r = self.results["SynthA4"]
        assert r["r32_count"] == 0, (
            f"Expected 0 / {N_SIMS} sims advancing but got {r['r32_count']}"
        )
        assert r["r32_pct"] == 0.0, (
            f"SynthA4 R32 = {r['r32_pct']:.6%} — should be exactly 0.000000%"
        )

    def test_eliminated_team_never_enters_third_place_pool(self):
        """SynthA4 is 4th — it should appear in neither top-2 nor best-third counts."""
        r = self.results["SynthA4"]
        assert r["r32_top2_count"]  == 0
        assert r["r32_third_count"] == 0

    # ── Consistency check ─────────────────────────────────────────────────────

    def test_group_a_counts_sum_to_2x_n_sims(self):
        """
        Every sim promotes exactly 2 top-2 teams from Group A.
        SynthA3 may additionally advance as best-third (or not — depends on
        global tiebreak), but r32_top2_count across all 4 Group A teams
        must equal exactly 2 * N_SIMS.
        """
        top2_total = sum(
            self.results[f"SynthA{i}"]["r32_top2_count"]
            for i in range(1, 5)
        )
        assert top2_total == 2 * N_SIMS, (
            f"Group A top-2 total = {top2_total}, expected {2 * N_SIMS}"
        )

    def test_all_groups_top2_total(self):
        """
        Summing r32_top2_count across all 48 teams must equal 24 * N_SIMS
        (2 teams × 12 groups × N_SIMS sims).
        """
        total = sum(r["r32_top2_count"] for r in self.results.values())
        assert total == 24 * N_SIMS, (
            f"Global top-2 total = {total}, expected {24 * N_SIMS}"
        )

    def test_best_third_total(self):
        """
        Summing r32_third_count across all 48 teams must equal 8 * N_SIMS
        (8 best thirds × N_SIMS sims).
        """
        total = sum(r["r32_third_count"] for r in self.results.values())
        assert total == 8 * N_SIMS, (
            f"Global best-third total = {total}, expected {8 * N_SIMS}"
        )


class TestMiddleCase:
    """
    SynthA3 — the 3-point third-placer — must return a rate strictly between
    0 % and 100 %, confirming the distribution responds to genuine stochastic
    uncertainty rather than clamping to the edges.

    Setup:
      Group A (partially played): SynthA3 has 3 pts / GD=−2 with one match left
        (vs SynthA4, p_home=0.40, p_draw=0.30, p_away=0.30).
      Groups B-I (fully played): each third-place team has 3 pts / GD=0.
      Groups J-L (fully played): each third-place team has 3 pts / GD=−4.

    Third-place ranking threshold:
      8 best thirds advance.  With 8 groups (B-I) occupying ranks 1-8 at GD=0,
      SynthA3 is 9th-best if it stays at 3 pts (any loss outcome) → 0 % R32.
      After a win or draw SynthA3 reaches 6 or 4 pts → clearly top-8 third → R32.

    Expected rate:  P(win) + P(draw) = 0.40 + 0.30 = 0.70
    Bound check:    0.60 < r32_pct < 0.80  (well beyond ±10 σ at 50 k sims)
    """

    def setup_method(self):
        played, remaining, team_group = _build_middle_case_data()
        self.results, _ = simulate_group_stage(
            played, remaining, team_group, n_sims=N_SIMS, seed=SEED
        )

    def test_synth_a3_is_non_trivial(self):
        """SynthA3's R32 rate must be strictly between 0 and 1."""
        r = self.results["SynthA3"]
        pct = r["r32_pct"]
        assert 0.0 < pct < 1.0, (
            f"SynthA3 R32 = {pct:.4%} — expected a value strictly between 0 % and 100 %"
        )

    def test_synth_a3_near_expected_rate(self):
        """
        SynthA3 R32 should be close to P(not-lose) = 0.70.
        Bound [0.60, 0.80] is ±10 σ at 50 k sims — failure means a logic bug,
        not simulation noise.
        """
        pct = self.results["SynthA3"]["r32_pct"]
        assert 0.60 < pct < 0.80, (
            f"SynthA3 R32 = {pct:.4%} — expected ≈70 % (win+draw), "
            f"got outside [60 %, 80 %] which indicates a conditioning bug"
        )

    def test_global_invariants_hold_with_remaining_matches(self):
        """
        The three global invariants must hold even when some matches are
        stochastic (Group A has 2 remaining fixtures).
        """
        top2_total  = sum(r["r32_top2_count"]  for r in self.results.values())
        third_total = sum(r["r32_third_count"] for r in self.results.values())

        assert top2_total == 24 * N_SIMS, (
            f"Global top-2 total = {top2_total}, expected {24 * N_SIMS}"
        )
        assert third_total == 8 * N_SIMS, (
            f"Global best-third total = {third_total}, expected {8 * N_SIMS}"
        )

    def test_r32_equals_top2_plus_third_for_every_team(self):
        """r32_count must equal r32_top2_count + r32_third_count for every team."""
        for team, r in self.results.items():
            assert r["r32_count"] == r["r32_top2_count"] + r["r32_third_count"], (
                f"{team}: r32={r['r32_count']} ≠ top2={r['r32_top2_count']} "
                f"+ third={r['r32_third_count']}"
            )
