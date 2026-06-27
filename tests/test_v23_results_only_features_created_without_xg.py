import pandas as pd

from tests.v23_test_helpers import run_results_only_backtest


def test_v23_results_only_features_created_without_xg(tmp_path):
    run_results_only_backtest(tmp_path)
    features = pd.read_csv(tmp_path / "out" / "match_1" / "winner_feature_store.csv")
    assert bool(features.loc[0, "xg_missing"])
    assert features.loc[0, "league_prediction_tier"] == "TIER_2_RESULTS_ONLY"

