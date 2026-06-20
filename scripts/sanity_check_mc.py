"""
Quick sanity check for the Monte Carlo group-stage simulator.

Group B after 2 matchdays:
  Canada      4 pts / +6 GD  — R32 should be very high (~100%)
  Switzerland 4 pts / +3 GD  — R32 should be very high (~100%)
  Bosnia      1 pt  / -3 GD  — low, but NOT mathematically 0% (they can win
                                their final match vs Qatar and end at 4 pts,
                                potentially qualifying as a best third-placed team)
  Qatar       1 pt  / -6 GD  — lower still, same logic applies

NOTE on Bosnia/Qatar "not eliminated" math:
  Bosnia's remaining match is vs Qatar.  If Bosnia wins, they reach 4 pts
  and become Group B's third-placed team.  With 8 best thirds advancing
  across 12 groups, a 4-pt third-place finish CAN qualify.  So ~30-70% R32
  for Bosnia via third-place is expected, not a bug.

  Qatar has worse GD (-6), so even after a win they trail most thirds → lower %.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import logging
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

from src.intelligence_layer.monte_carlo import load_current_state, simulate_group_stage, N_SIMS

DB_PATH          = "data/tempo.db"
PREDICTIONS_PATH = "predictions.parquet"

print(f"\nLoading data from {DB_PATH} and {PREDICTIONS_PATH} ...")
played, remaining, team_group, elo_ratings = load_current_state(DB_PATH, PREDICTIONS_PATH)
print(f"  Played fixtures   : {len(played)}")
print(f"  Remaining fixtures: {len(remaining)}")
print(f"  Teams in sim      : {len(team_group)}")

print(f"\nRunning {N_SIMS:,} Monte Carlo simulations (seed=42) ...")
results, group_teams = simulate_group_stage(played, remaining, team_group)
print("  Done.\n")

# ── Sanity checks ──────────────────────────────────────────────────────────────
# (lo, hi) are wide-enough bands to catch genuine bugs without flagging
# plausible third-place advancement paths.
CHECKS = [
    # team,                    lo,    hi,    note
    ("Canada",                 0.97,  1.00,  "Group B: 4pts/+6GD — guaranteed-ish top-2"),
    ("Switzerland",            0.97,  1.00,  "Group B: 4pts/+3GD — guaranteed-ish top-2"),
    ("Bosnia and Herzegovina", 0.20,  0.75,  "Group B: 1pt/-3GD  — low but non-zero (best-third route)"),
    ("Qatar",                  0.05,  0.45,  "Group B: 1pt/-6GD  — lower still, same logic"),
]

print("=" * 72)
print("SANITY CHECKS")
print("=" * 72)
all_pass = True
for team, lo, hi, note in CHECKS:
    if team not in results:
        print(f"  MISSING : {team}")
        all_pass = False
        continue
    r = results[team]
    pct = r["r32_pct"]
    status = "PASS" if lo <= pct <= hi else "FAIL"
    if status == "FAIL":
        all_pass = False
    print(f"  {status:4s} | {team:<30s} R32={pct:6.1%}  "
          f"(top2={r['r32_top2_pct']:.1%}, via3rd={r['r32_third_pct']:.1%})  -- {note}")

print()
if all_pass:
    print("All sanity checks PASSED.")
else:
    print("One or more sanity checks FAILED -- review conditioning logic.")

# ── Full group-by-group summary ───────────────────────────────────────────────
print()
print("=" * 72)
print("R32 ADVANCEMENT ODDS -- ALL GROUPS")
print("=" * 72)

GROUPS = list("ABCDEFGHIJKL")
for grp in GROUPS:
    if grp not in group_teams:
        continue
    print(f"\n  Group {grp}")
    for team in sorted(group_teams[grp], key=lambda t: -results[t]["r32_pct"]):
        r = results[team]
        bar_len = round(r["r32_pct"] * 25)
        bar = "#" * bar_len + "." * (25 - bar_len)
        pct_str = f"{r['r32_pct']:6.1%}"
        # truncate team name for alignment
        tname = (team[:26] + "..") if len(team) > 28 else team
        print(f"    {tname:<28s} {pct_str}  [{bar}]"
              f"  top2={r['r32_top2_pct']:.1%}  via3rd={r['r32_third_pct']:.1%}")

print()
