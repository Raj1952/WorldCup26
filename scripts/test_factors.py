import json, sys, logging
logging.basicConfig(level=logging.WARNING)
sys.path.insert(0, ".")
from src.intelligence_layer.predict import predict_upcoming

df = predict_upcoming()
if df.empty:
    print("No predictions generated")
    sys.exit(1)

row = df.iloc[0]
factors = row["top_factors"]
if isinstance(factors, str):
    factors = json.loads(factors)

print(f"{row['home_team']} vs {row['away_team']}")
print(f"p_home={row['p_home']:.1%}  p_draw={row['p_draw']:.1%}  p_away={row['p_away']:.1%}")
print("Factors:", factors)

has_factors = 0
for _, r in df.iterrows():
    f = r["top_factors"]
    if isinstance(f, str):
        f = json.loads(f)
    if f:
        has_factors += 1

print(f"\n{has_factors}/{len(df)} predictions have factors")
