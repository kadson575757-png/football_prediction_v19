import pandas as pd

from tests.v23_test_helpers import run_results_only_backtest


def test_v23_early_season_is_risk_not_block(tmp_path):
    result = run_results_only_backtest(tmp_path)
    features = pd.read_csv(tmp_path / "out" / "match_1" / "winner_feature_store.csv")
    assert bool(features.loc[0, "early_season_risk"])
    assert result["data_blocked_count"] == 0

