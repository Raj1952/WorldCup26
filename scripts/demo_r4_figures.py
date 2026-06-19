"""
R4 demo — renders ternary and two waterfalls as HTML files.

Usage:
    python scripts/demo_r4_figures.py
"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from src.presentation_layer.charts.ternary import ternary_scatter
from src.presentation_layer.charts.waterfall import prediction_waterfall

# Load predictions
df = pd.read_parquet("predictions.parquet")
df["top_factors"] = df["top_factors"].apply(
    lambda x: json.loads(x) if isinstance(x, str) else (x if isinstance(x, list) else [])
)
upcoming = df[df["group_label"].str.match(r"^[A-L]$", na=False)].reset_index(drop=True)

print(f"Loaded {len(upcoming)} group-stage matches.")

# ── Ternary ───────────────────────────────────────────────────────────────────
fig_tern = ternary_scatter(upcoming)
out_tern = Path("artifacts/reports/r4_ternary.html")
out_tern.parent.mkdir(parents=True, exist_ok=True)
fig_tern.write_html(str(out_tern), include_plotlyjs="cdn", full_html=True)
print(f"Ternary written: {out_tern}")

# ── Waterfall — Match 1: Brazil vs Haiti (strong home favourite) ──────────────
m1 = upcoming[upcoming["home_team"] == "Brazil"].iloc[0]
fig_wf1 = prediction_waterfall(m1)

# Print the waterfall steps for validation
base = 1/3
factors = m1["top_factors"]
signed = [
    float(f["impact"]) if f.get("direction", "+") == "+" else -float(f["impact"])
    for f in factors
]
total_signed = sum(signed)
scale = (m1["p_home"] - base) / total_signed if abs(total_signed) > 1e-9 else 0
steps = [s * scale for s in signed]

print(f"\nMatch 1: {m1['home_team']} vs {m1['away_team']}")
print(f"  p_home={m1['p_home']:.4f} p_draw={m1['p_draw']:.4f} p_away={m1['p_away']:.4f}")
print(f"  base_rate = {base:.4f}")
print(f"  total_signed_raw = {total_signed:.4f}")
print(f"  scale = {scale:.4f}")
acc = base
for f, s in zip(factors, steps):
    acc += s
    print(f"  {f['label']} ({f['direction']}) raw={f['impact']:.4f} "
          f"scaled={s:+.4f}  running={acc:.4f}")
print(f"  Final (calibrated p_home): {m1['p_home']:.4f}  Delta from running: {abs(acc - m1['p_home']):.6f}")

out_wf1 = Path("artifacts/reports/r4_waterfall_m1.html")
fig_wf1.write_html(str(out_wf1), include_plotlyjs="cdn", full_html=True)
print(f"Waterfall 1 written: {out_wf1}")

# ── Waterfall — Match 2: Scotland vs Morocco (away favourite) ─────────────────
m2 = upcoming[upcoming["home_team"] == "Scotland"].iloc[0]
fig_wf2 = prediction_waterfall(m2)

factors2 = m2["top_factors"]
signed2 = [
    float(f["impact"]) if f.get("direction", "+") == "+" else -float(f["impact"])
    for f in factors2
]
total_signed2 = sum(signed2)
scale2 = (m2["p_home"] - base) / total_signed2 if abs(total_signed2) > 1e-9 else 0
steps2 = [s * scale2 for s in signed2]

print(f"\nMatch 2: {m2['home_team']} vs {m2['away_team']}")
print(f"  p_home={m2['p_home']:.4f} p_draw={m2['p_draw']:.4f} p_away={m2['p_away']:.4f}")
print(f"  base_rate = {base:.4f}")
print(f"  total_signed_raw = {total_signed2:.4f}")
print(f"  scale = {scale2:.4f}")
acc2 = base
for f, s in zip(factors2, steps2):
    acc2 += s
    print(f"  {f['label']} ({f['direction']}) raw={f['impact']:.4f} "
          f"scaled={s:+.4f}  running={acc2:.4f}")
print(f"  Final (calibrated p_home): {m2['p_home']:.4f}  Delta from running: {abs(acc2 - m2['p_home']):.6f}")

out_wf2 = Path("artifacts/reports/r4_waterfall_m2.html")
fig_wf2.write_html(str(out_wf2), include_plotlyjs="cdn", full_html=True)
print(f"Waterfall 2 written: {out_wf2}")

print("\nOpen these in a browser to inspect:")
print(f"  {out_tern.resolve()}")
print(f"  {out_wf1.resolve()}")
print(f"  {out_wf2.resolve()}")
