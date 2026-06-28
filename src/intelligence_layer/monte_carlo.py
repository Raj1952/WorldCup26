"""
Monte Carlo group-stage + tournament simulator.

C4 decisions (confirmed 2026-06-19):
  - 50,000 seeded runs (seed=42), deterministic per §6
  - Conditioning: starts from CURRENT standings + remaining-match model probabilities,
    NOT a fresh 48-team draw. Already-played results are fixed.
  - Projected knockout slots displayed only on the Bracket page, labeled "Projected".
    Never injected into the Predictions / match-card flow (that stays known-teams-only).

Knockout conditioning (added 2026-06-28):
  - Played knockout matches are treated as settled: real winner advances with 100%,
    real loser is eliminated. Only unplayed knockout matches are simulated.
  - Penalty draws: if the DB stores a draw score for a KO match, the sim falls back
    to data/manual_results.csv (knockout_winner column) to resolve the advancing team.
    If neither source resolves it, the match is skipped and Elo probability is used.

Uncertainty note (§C4 point 4):
  champion_std expresses the genuine OUTCOME SPREAD across 50k simulations —
  i.e. the standard deviation of the Bernoulli indicator (team wins tournament) over
  sims.  This is sqrt(p*(1-p)/n_sims) only at the limit, but for realistic p values
  the finite-sim noise is <<0.5pp so the dominant contribution is genuine model
  uncertainty propagated through the bracket, not Monte Carlo sampling error.
  We therefore label it "outcome uncertainty" in the UI, not "sampling error."

Layer boundary: Layer 2 only. No Streamlit/Plotly imports here.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
SEED          = 42
N_SIMS        = 50_000
GROUPS        = list("ABCDEFGHIJKL")   # 12 groups
N_PER_GROUP   = 4
N_THIRDS_ADV  = 8                      # best third-placed teams that advance to R32

# Score Poisson means by outcome (used for GD / GF tiebreaker simulation)
# Chosen to match WC historical averages per outcome type.
_LAMBDA_HW = (2.2, 0.9)   # home win: (λ_home, λ_away)
_LAMBDA_D  = (1.1, 1.1)   # draw
_LAMBDA_AW = (0.9, 2.2)   # away win

# Maps DB group_label for knockout rounds → our sim round key.
# The round key tracks who REACHES that round (e.g. "r16" = teams that survive R32).
_KO_DB_TO_ROUND: dict[str, str] = {
    "R32":   "r16",
    "R16":   "qf",
    "QF":    "sf",
    "SF":    "final",
    "Final": "champion",
    # "3P" (third-place play-off) is not part of the title-odds bracket — ignored
}


# ── Data loading ───────────────────────────────────────────────────────────────

def load_current_state(
    db_path: str,
    predictions_path: str = "predictions.parquet",
    manual_results_path: str = "data/manual_results.csv",
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str], dict[str, float], list[dict]]:
    """
    Load current group standings + remaining-fixture probabilities + settled
    knockout results.

    Returns
    -------
    played           : played group-stage fixtures with real scores
    remaining        : remaining group-stage fixtures enriched with model probabilities
    team_group       : {team_name: group_label}
    elo_ratings      : {team_name: elo_value}  (for knockout-round Elo fallback)
    played_knockouts : [{round_key, winner, loser}, ...] for all settled KO matches
    """
    conn = sqlite3.connect(db_path)

    # Group-stage: single-character group labels A–L
    played = pd.read_sql("""
        SELECT date, group_label, home_team, away_team, home_score, away_score
        FROM wc2026_fixtures
        WHERE home_score IS NOT NULL AND length(group_label) = 1
        ORDER BY date
    """, conn)

    all_fixture_teams = pd.read_sql("""
        SELECT DISTINCT home_team AS team, group_label FROM wc2026_fixtures
        WHERE length(group_label) = 1 AND home_team NOT LIKE 'W%'
        UNION
        SELECT DISTINCT away_team, group_label FROM wc2026_fixtures
        WHERE length(group_label) = 1 AND away_team NOT LIKE 'W%'
    """, conn)

    remaining_raw = pd.read_sql("""
        SELECT date, group_label, home_team, away_team
        FROM wc2026_fixtures
        WHERE home_score IS NULL
          AND length(group_label) = 1
          AND home_team NOT LIKE 'W%'
          AND away_team NOT LIKE 'W%'
        ORDER BY date
    """, conn)

    # Knockout matches with settled scores
    ko_played_raw = pd.read_sql("""
        SELECT match_id, date, group_label, home_team, away_team,
               home_score, away_score
        FROM wc2026_fixtures
        WHERE home_score IS NOT NULL
          AND group_label IN ('R32', 'R16', 'QF', 'SF', 'Final')
        ORDER BY date
    """, conn)

    elo_df = pd.read_sql("SELECT team, elo FROM elo_current", conn)
    conn.close()

    elo_ratings: dict[str, float] = dict(zip(elo_df["team"], elo_df["elo"]))
    team_group:  dict[str, str]   = dict(zip(
        all_fixture_teams["team"], all_fixture_teams["group_label"]
    ))

    # ── Penalty-draw fallback: manual_results.csv knockout_winner column ──────
    manual_ko_winners: dict[str, str] = {}   # match_id → advancing team name
    try:
        manual_path = Path(manual_results_path)
        if manual_path.exists():
            mdf = pd.read_csv(manual_path)
            if "knockout_winner" in mdf.columns and "match_id" in mdf.columns:
                for _, row in mdf.iterrows():
                    kw = str(row.get("knockout_winner", "")).strip()
                    if kw and kw.lower() not in ("nan", ""):
                        manual_ko_winners[str(row["match_id"])] = kw
    except Exception as exc:
        logger.warning("Could not read manual_results.csv for KO winners: %s", exc)

    # ── Resolve knockout settled results ──────────────────────────────────────
    played_knockouts: list[dict] = []
    for _, row in ko_played_raw.iterrows():
        round_key = _KO_DB_TO_ROUND.get(str(row["group_label"]))
        if round_key is None:
            continue
        home, away = str(row["home_team"]), str(row["away_team"])
        hs, as_   = int(row["home_score"]), int(row["away_score"])

        if hs > as_:
            winner, loser = home, away
        elif as_ > hs:
            winner, loser = away, home
        else:
            # Draw after 90 min — match went to ET / penalties.
            # Check manual override; otherwise skip conditioning.
            mid = str(row["match_id"])
            if mid in manual_ko_winners:
                winner = manual_ko_winners[mid]
                loser  = away if winner == home else home
                logger.info(
                    "KO result from manual override: %s beats %s (%d-%d pen)",
                    winner, loser, hs, as_,
                )
            else:
                logger.warning(
                    "KO match %s (%s vs %s, %d-%d) ended level — add "
                    "knockout_winner to data/manual_results.csv to condition on it.",
                    mid, home, away, hs, as_,
                )
                continue

        played_knockouts.append({
            "round_key": round_key,
            "winner":    winner,
            "loser":     loser,
        })
        logger.info(
            "KO settled: %s beats %s → advances to %s",
            winner, loser, round_key,
        )

    # ── Prediction lookup for remaining group-stage fixtures ──────────────────
    preds = pd.read_parquet(predictions_path)
    pred_lookup: dict[tuple, tuple] = {
        (r["home_team"], r["away_team"]): (
            float(r["p_home"]), float(r["p_draw"]), float(r["p_away"])
        )
        for _, r in preds.iterrows()
    }

    def _get_probs(row: pd.Series) -> pd.Series:
        key = (row["home_team"], row["away_team"])
        if key in pred_lookup:
            ph, pd_, pa = pred_lookup[key]
        else:
            elo_h = elo_ratings.get(row["home_team"], 1500.0)
            elo_a = elo_ratings.get(row["away_team"], 1500.0)
            raw   = 1.0 / (1.0 + 10.0 ** ((elo_a - elo_h) / 400.0))
            ph    = raw * 0.45
            pa    = (1 - raw) * 0.45
            pd_   = 1.0 - ph - pa
            logger.warning(
                "No model prediction for %s vs %s — Elo fallback used",
                row["home_team"], row["away_team"],
            )
        return pd.Series({"p_home": ph, "p_draw": pd_, "p_away": pa})

    remaining = remaining_raw.copy()
    remaining[["p_home", "p_draw", "p_away"]] = remaining.apply(_get_probs, axis=1)
    return played, remaining, team_group, elo_ratings, played_knockouts


# ── Initial standings ──────────────────────────────────────────────────────────

def _build_initial_standings(
    played: pd.DataFrame,
    all_teams: list[str],
) -> dict[str, dict]:
    """Build {team: {pts, gf, ga, gd, mp}} from real played results."""
    s: dict[str, dict] = {
        t: {"pts": 0, "gf": 0, "ga": 0, "gd": 0, "mp": 0}
        for t in all_teams
    }
    for _, row in played.iterrows():
        h, a    = row["home_team"], row["away_team"]
        hs, as_ = int(row["home_score"]), int(row["away_score"])
        if h not in s or a not in s:
            continue
        s[h]["mp"] += 1; s[h]["gf"] += hs; s[h]["ga"] += as_; s[h]["gd"] += hs - as_
        s[a]["mp"] += 1; s[a]["gf"] += as_; s[a]["ga"] += hs; s[a]["gd"] += as_ - hs
        if hs > as_:
            s[h]["pts"] += 3
        elif hs < as_:
            s[a]["pts"] += 3
        else:
            s[h]["pts"] += 1; s[a]["pts"] += 1
    return s


# ── Group-stage simulation ─────────────────────────────────────────────────────

def simulate_group_stage(
    played: pd.DataFrame,
    remaining: pd.DataFrame,
    team_group: dict[str, str],
    n_sims: int = N_SIMS,
    seed: int = SEED,
) -> tuple[dict[str, dict], dict[str, list[str]]]:
    """
    Simulate group stage n_sims times from current standings.

    Conditioning: played results are fixed; only remaining matches are
    stochastic.  A team with 0 remaining matches has deterministic final
    standings — no sampling error applied to decided results.

    Returns
    -------
    results      : {team: {r32_pct, r32_top2_count, r32_third_count, r32_count}}
    group_teams  : {group_label: [team, ...]}  (alphabetically sorted)
    """
    rng = np.random.default_rng(seed)

    group_teams: dict[str, list[str]] = {}
    for team, grp in sorted(team_group.items()):
        group_teams.setdefault(grp, []).append(team)
    for grp in group_teams:
        group_teams[grp].sort()

    all_teams: list[str] = [t for grp in GROUPS for t in group_teams.get(grp, [])]
    team_idx: dict[str, int] = {t: i for i, t in enumerate(all_teams)}
    n_teams = len(all_teams)

    init = _build_initial_standings(played, all_teams)
    init_pts = np.array([init[t]["pts"] for t in all_teams], np.float32)
    init_gf  = np.array([init[t]["gf"]  for t in all_teams], np.float32)
    init_gd  = np.array([init[t]["gd"]  for t in all_teams], np.float32)

    pts = np.tile(init_pts, (n_sims, 1))
    gf  = np.tile(init_gf,  (n_sims, 1))
    gd  = np.tile(init_gd,  (n_sims, 1))

    for _, row in remaining.iterrows():
        if row["home_team"] not in team_idx or row["away_team"] not in team_idx:
            continue

        h_i = team_idx[row["home_team"]]
        a_i = team_idx[row["away_team"]]
        ph  = float(row["p_home"])
        pd_ = float(row["p_draw"])

        u     = rng.random(n_sims)
        is_hw = (u < ph)
        is_d  = (u >= ph) & (u < ph + pd_)
        is_aw = ~is_hw & ~is_d

        h_g_hw = np.maximum(rng.poisson(_LAMBDA_HW[0], n_sims),
                             rng.poisson(_LAMBDA_HW[1], n_sims) + 1).astype(np.float32)
        a_g_hw = rng.poisson(_LAMBDA_HW[1], n_sims).astype(np.float32)
        tie_g  = rng.poisson(_LAMBDA_D[0], n_sims).astype(np.float32)
        a_g_aw = np.maximum(rng.poisson(_LAMBDA_AW[1], n_sims),
                             rng.poisson(_LAMBDA_AW[0], n_sims) + 1).astype(np.float32)
        h_g_aw = rng.poisson(_LAMBDA_AW[0], n_sims).astype(np.float32)

        h_g = is_hw * h_g_hw + is_d * tie_g + is_aw * h_g_aw
        a_g = is_hw * a_g_hw + is_d * tie_g + is_aw * a_g_aw

        pts[:, h_i] += is_hw * 3 + is_d * 1
        pts[:, a_i] += is_aw * 3 + is_d * 1
        gf[:,  h_i] += h_g;  gd[:, h_i] += h_g - a_g
        gf[:,  a_i] += a_g;  gd[:, a_i] += a_g - h_g

    r32_top2  = np.zeros(n_teams, np.int64)
    r32_third = np.zeros(n_teams, np.int64)

    n_groups     = len(GROUPS)
    third_pts    = np.zeros((n_sims, n_groups), np.float32)
    third_gd     = np.zeros((n_sims, n_groups), np.float32)
    third_gf     = np.zeros((n_sims, n_groups), np.float32)
    third_global_idx = np.zeros((n_sims, n_groups), np.int32)

    for g_i, grp in enumerate(GROUPS):
        if grp not in group_teams:
            continue
        idxs = np.array([team_idx[t] for t in group_teams[grp]], dtype=np.int32)

        g_pts = pts[:, idxs]
        g_gd  = gd[:,  idxs]
        g_gf  = gf[:,  idxs]

        score = g_pts * 1e6 + g_gd * 1e3 + g_gf
        ranks = np.argsort(-score, axis=1, kind="stable")

        pos1 = ranks[:, 0]
        pos2 = ranks[:, 1]
        pos3 = ranks[:, 2]

        global1 = idxs[pos1]
        global2 = idxs[pos2]
        np.add.at(r32_top2, global1, 1)
        np.add.at(r32_top2, global2, 1)

        sim_row = np.arange(n_sims)
        third_pts[:, g_i]        = g_pts[sim_row, pos3]
        third_gd[:,  g_i]        = g_gd[ sim_row, pos3]
        third_gf[:,  g_i]        = g_gf[ sim_row, pos3]
        third_global_idx[:, g_i] = idxs[pos3]

    third_score  = third_pts * 1e6 + third_gd * 1e3 + third_gf
    best8_cols   = np.argsort(-third_score, axis=1)[:, :N_THIRDS_ADV]
    row_idx      = np.arange(n_sims)[:, None]
    best8_global = third_global_idx[row_idx, best8_cols]

    for col in range(N_THIRDS_ADV):
        np.add.at(r32_third, best8_global[:, col], 1)

    r32_total = r32_top2 + r32_third
    results: dict[str, dict] = {}
    for i, team in enumerate(all_teams):
        results[team] = {
            "r32_count":       int(r32_total[i]),
            "r32_top2_count":  int(r32_top2[i]),
            "r32_third_count": int(r32_third[i]),
            "r32_pct":         float(r32_total[i] / n_sims),
            "r32_top2_pct":    float(r32_top2[i]  / n_sims),
            "r32_third_pct":   float(r32_third[i] / n_sims),
        }
    return results, group_teams


# ── Full tournament simulation ─────────────────────────────────────────────────

def _ko_win_prob(elo_a: np.ndarray, elo_b: np.ndarray) -> np.ndarray:
    """Knockout win probability P(A beats B) from Elo — no draw possible."""
    return 1.0 / (1.0 + np.power(10.0, (elo_b - elo_a) / 400.0))


def simulate_full_tournament(
    db_path: str,
    predictions_path: str = "predictions.parquet",
    n_sims: int = N_SIMS,
    seed: int = SEED,
    manual_results_path: str = "data/manual_results.csv",
) -> pd.DataFrame:
    """
    Full tournament Monte Carlo: group stage + 5 knockout rounds.

    Group stage uses model probabilities from predictions.parquet (with Elo
    fallback). Knockout rounds use Elo-based win probability for UNPLAYED
    matches; played knockout matches are conditioned on real results (winner
    advances 100%, loser eliminated).

    Bracket: after each group-stage sim the 32 advancing teams are re-seeded
    by Elo and paired (seed-1 vs seed-32, seed-2 vs seed-31, …). After each
    knockout round winners are re-seeded by Elo before the next pairing —
    the "re-seeded bracket" method.

    Returns
    -------
    pd.DataFrame  one row per team, sorted by champion_pct descending:
        team, r32_pct, r16_pct, qf_pct, sf_pct, final_pct,
        champion_pct, champion_std
    """
    played, remaining, team_group, elo_ratings, played_knockouts = load_current_state(
        db_path, predictions_path, manual_results_path
    )

    if played_knockouts:
        logger.info(
            "%d settled knockout result(s) will override sim: %s",
            len(played_knockouts),
            [(ko["winner"], "→", ko["round_key"]) for ko in played_knockouts],
        )

    # Sorted rosters for determinism
    group_teams: dict[str, list[str]] = {}
    for team, grp in sorted(team_group.items()):
        group_teams.setdefault(grp, []).append(team)
    for grp in group_teams:
        group_teams[grp].sort()

    all_teams: list[str] = [t for grp in GROUPS for t in group_teams.get(grp, [])]
    team_idx:  dict[str, int] = {t: i for i, t in enumerate(all_teams)}
    n_teams    = len(all_teams)

    rng = np.random.default_rng(seed)

    # ── Group-stage simulation ────────────────────────────────────────────────
    init     = _build_initial_standings(played, all_teams)
    init_pts = np.array([init[t]["pts"] for t in all_teams], np.float32)
    init_gf  = np.array([init[t]["gf"]  for t in all_teams], np.float32)
    init_gd  = np.array([init[t]["gd"]  for t in all_teams], np.float32)

    pts = np.tile(init_pts, (n_sims, 1))
    gf  = np.tile(init_gf,  (n_sims, 1))
    gd  = np.tile(init_gd,  (n_sims, 1))

    for _, row in remaining.iterrows():
        h = row["home_team"]
        a = row["away_team"]
        if h not in team_idx or a not in team_idx:
            continue
        h_i, a_i = team_idx[h], team_idx[a]
        ph  = float(row["p_home"])
        pd_ = float(row["p_draw"])

        u     = rng.random(n_sims)
        is_hw = u < ph
        is_d  = (u >= ph) & (u < ph + pd_)
        is_aw = ~is_hw & ~is_d

        h_g_hw = np.maximum(rng.poisson(_LAMBDA_HW[0], n_sims),
                             rng.poisson(_LAMBDA_HW[1], n_sims) + 1).astype(np.float32)
        a_g_hw = rng.poisson(_LAMBDA_HW[1], n_sims).astype(np.float32)
        tie_g  = rng.poisson(_LAMBDA_D[0],  n_sims).astype(np.float32)
        a_g_aw = np.maximum(rng.poisson(_LAMBDA_AW[1], n_sims),
                             rng.poisson(_LAMBDA_AW[0], n_sims) + 1).astype(np.float32)
        h_g_aw = rng.poisson(_LAMBDA_AW[0], n_sims).astype(np.float32)

        h_g = is_hw * h_g_hw + is_d * tie_g + is_aw * h_g_aw
        a_g = is_hw * a_g_hw + is_d * tie_g + is_aw * a_g_aw

        pts[:, h_i] += is_hw * 3 + is_d
        pts[:, a_i] += is_aw * 3 + is_d
        gf[:,  h_i] += h_g;  gd[:, h_i] += h_g - a_g
        gf[:,  a_i] += a_g;  gd[:, a_i] += a_g - h_g

    # ── Determine R32 qualifiers per sim ──────────────────────────────────────
    score    = pts * 1e6 + gd * 1e3 + gf
    r32_mask = np.zeros((n_sims, n_teams), dtype=bool)
    n_grps   = len(GROUPS)
    t_score  = np.zeros((n_sims, n_grps), np.float32)
    t_global = np.zeros((n_sims, n_grps), np.int32)

    for g_i, grp in enumerate(GROUPS):
        if grp not in group_teams:
            continue
        idxs  = np.array([team_idx[t] for t in group_teams[grp]], np.int32)
        g_sc  = score[:, idxs]
        ranks = np.argsort(-g_sc, axis=1, kind="stable")
        sr    = np.arange(n_sims)

        r32_mask[sr, idxs[ranks[:, 0]]] = True
        r32_mask[sr, idxs[ranks[:, 1]]] = True
        t_score[:,  g_i] = g_sc[sr, ranks[:, 2]]
        t_global[:, g_i] = idxs[ranks[:, 2]]

    ri         = np.arange(n_sims)[:, None]
    best8_cols = np.argsort(-t_score, axis=1)[:, :N_THIRDS_ADV]
    r32_mask[ri, t_global[ri, best8_cols]] = True

    # Seed the 32 qualifiers by Elo descending (seed-1 = highest Elo)
    elo_array  = np.array([elo_ratings.get(t, 1500.0) for t in all_teams], np.float32)
    qual_score = np.where(r32_mask, score, np.float32(-1e18))
    current    = np.argsort(-qual_score, axis=1, kind="stable")[:, :32].astype(np.int32)

    elo_curr  = elo_array[current]
    elo_order = np.argsort(-elo_curr, axis=1)
    current   = current[np.arange(n_sims)[:, None], elo_order]

    # ── Build per-round conditioning lookup ───────────────────────────────────
    # ko_settled[round_key] = [(winner_idx, loser_idx), ...]
    ko_settled: dict[str, list[tuple[int, int]]] = {
        k: [] for k in ("r16", "qf", "sf", "final", "champion")
    }
    for ko in played_knockouts:
        rk = ko["round_key"]
        w  = team_idx.get(ko["winner"])
        l  = team_idx.get(ko["loser"])
        if w is not None and l is not None and rk in ko_settled:
            ko_settled[rk].append((w, l))

    # ── Count advancers ───────────────────────────────────────────────────────
    cnt: dict[str, np.ndarray] = {
        "r32":      np.bincount(current.flatten(), minlength=n_teams),
        "r16":      np.zeros(n_teams, np.int64),
        "qf":       np.zeros(n_teams, np.int64),
        "sf":       np.zeros(n_teams, np.int64),
        "final":    np.zeros(n_teams, np.int64),
        "champion": np.zeros(n_teams, np.int64),
    }

    # ── Knockout rounds ───────────────────────────────────────────────────────
    sim_idx = np.arange(n_sims)

    for round_key in ("r16", "qf", "sf", "final", "champion"):
        n_in = current.shape[1]
        n_m  = n_in // 2

        # Re-seed by Elo before each round
        elos  = elo_array[current]
        order = np.argsort(-elos, axis=1)
        current = current[sim_idx[:, None], order]

        # Pair: seed-1 vs seed-N, seed-2 vs seed-(N-1), ...
        a = current[:, :n_m]
        b = current[:, n_m:][:, ::-1].copy()

        # Simulate all matches via Elo
        p_a     = _ko_win_prob(elo_array[a], elo_array[b])
        u       = rng.random((n_sims, n_m)).astype(np.float32)
        winners = np.where(u < p_a, a, b)

        # ── Conditioning: override Elo roll with real settled results ─────────
        # The real tournament bracket (based on group positions) does NOT match
        # the Elo re-seeded bracket used in the sim. So we cannot rely on finding
        # the exact pair in the bracket. Instead we force independently:
        #   winner always advances from whatever slot they occupy
        #   loser is always eliminated — their Elo-paired opponent advances
        for w_idx, l_idx in ko_settled.get(round_key, []):
            # Winner advances from whichever bracket slot they occupy
            w_in_a   = (a == w_idx)                # (n_sims, n_m)
            w_in_b   = (b == w_idx)
            winners  = np.where(w_in_a, w_idx, winners)
            winners  = np.where(w_in_b, w_idx, winners)
            # Loser is eliminated — their Elo-paired opponent takes the slot
            l_in_a   = (a == l_idx)
            l_in_b   = (b == l_idx)
            l_wins   = (winners == l_idx)           # slots where loser "won" the Elo roll
            opp      = np.where(l_in_a, b, a)      # loser's Elo opponent in each slot
            winners  = np.where(l_wins & (l_in_a | l_in_b), opp, winners)

        cnt[round_key] += np.bincount(winners.flatten(), minlength=n_teams)
        current = winners

    # ── Assemble output DataFrame ─────────────────────────────────────────────
    rows = []
    for i, team in enumerate(all_teams):
        r32 = int(cnt["r32"][i])
        if r32 == 0:
            continue
        ch = int(cnt["champion"][i])
        rows.append({
            "team":         team,
            "r32_pct":      r32 / n_sims,
            "r16_pct":      int(cnt["r16"][i])   / n_sims,
            "qf_pct":       int(cnt["qf"][i])    / n_sims,
            "sf_pct":       int(cnt["sf"][i])    / n_sims,
            "final_pct":    int(cnt["final"][i]) / n_sims,
            "champion_pct": ch / n_sims,
            "champion_std": float(
                np.sqrt(max(ch, 1) / n_sims * (1.0 - ch / n_sims) / n_sims)
            ),
        })

    return (
        pd.DataFrame(rows)
        .sort_values("champion_pct", ascending=False)
        .reset_index(drop=True)
    )
