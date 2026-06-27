from football_prediction_v19.analysis.v20_no_leakage_backtest_runner import run_no_leakage_backtest


def test_no_leakage_backtest_safety_no_roi_stake(tmp_path):
    result = run_no_leakage_backtest("tests/fixtures/v20_no_leakage_backtest/mini_season_matches_mock.csv", tmp_path, mock_data_dir="tests/fixtures/v20_no_leakage_backtest", max_matches=1)
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
