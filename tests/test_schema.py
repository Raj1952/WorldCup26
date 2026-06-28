"""
predictions.parquet schema contract test.
"""

import pytest
from pathlib import Path

PREDICTIONS_PATH = Path("predictions.parquet")
REQUIRED_COLS = {
    "match_id", "date", "home_team", "away_team",
    "p_home", "p_draw", "p_away",
    "top_factors", "model_version", "created_at",
}


@pytest.mark.skipif(not PREDICTIONS_PATH.exists(), reason="predictions.parquet not built yet")
def test_predictions_schema():
    import pandas as pd
    df = pd.read_parquet(PREDICTIONS_PATH)
    missing = REQUIRED_COLS - set(df.columns)
    assert not missing, f"Missing columns in predictions.parquet: {missing}"


@pytest.mark.skipif(not PREDICTIONS_PATH.exists(), reason="predictions.parquet not built yet")
def test_predictions_probabilities_sum():
    import pandas as pd
    import numpy as np
    df = pd.read_parquet(PREDICTIONS_PATH)
    # Only check rows with concrete predictions (projected slots have NaN probs by design)
    concrete = df[df["p_home"].notna()]
    if concrete.empty:
        pytest.skip("No concrete predictions in file yet")
    sums = concrete["p_home"] + concrete["p_draw"] + concrete["p_away"]
    assert np.allclose(sums, 1.0, atol=0.02), \
        f"Probabilities don't sum to 1.0: min={sums.min():.4f} max={sums.max():.4f}"


@pytest.mark.skipif(not PREDICTIONS_PATH.exists(), reason="predictions.parquet not built yet")
def test_predictions_no_null_teams():
    import pandas as pd
    df = pd.read_parquet(PREDICTIONS_PATH)
    assert df["home_team"].notna().all(), "NULL home_team in predictions"
    assert df["away_team"].notna().all(), "NULL away_team in predictions"


@pytest.mark.skipif(not PREDICTIONS_PATH.exists(), reason="predictions.parquet not built yet")
def test_predictions_valid_probs():
    import pandas as pd
    df = pd.read_parquet(PREDICTIONS_PATH)
    # Only validate concrete rows — projected slots intentionally carry NaN probs
    concrete = df[df["p_home"].notna()]
    if concrete.empty:
        pytest.skip("No concrete predictions in file yet")
    for col in ["p_home", "p_draw", "p_away"]:
        assert (concrete[col] >= 0).all() and (concrete[col] <= 1).all(), \
            f"{col} values out of [0,1] range"
