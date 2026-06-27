from tests.v23_test_helpers import run_results_only_backtest


def test_v23_backtest_probabilities_created_count(tmp_path):
    result = run_results_only_backtest(tmp_path)
    assert result["probabilities_created_count"] > 0

