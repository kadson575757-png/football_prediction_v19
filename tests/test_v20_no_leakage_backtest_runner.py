from football_prediction_v19.analysis.v20_no_leakage_backtest_runner import run_no_leakage_backtest


def test_no_leakage_backtest_runner_writes_outputs(tmp_path):
    result = run_no_leakage_backtest("tests/fixtures/v20_no_leakage_backtest/mini_season_matches_mock.csv", tmp_path, mock_data_dir="tests/fixtures/v20_no_leakage_backtest", max_matches=1)
    assert result["v20_no_leakage_backtest_status"] == "READY"
    assert result["matches_total"] == 1
    assert result["automatic_betting_enabled"] is False
    assert (tmp_path / "v20_no_leakage_backtest_results.csv").exists()
