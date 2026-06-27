from tests.v23_test_helpers import run_results_only_backtest


def test_v23_understat_failed_parse_does_not_block_results_only(tmp_path):
    result = run_results_only_backtest(tmp_path)
    assert result["understat_failed_non_block_count"] > 0
    assert result["invalid_data_blocked_count"] == 0

