from tests.v23_test_helpers import run_results_only_backtest


def test_v23_results_only_corpus_not_data_blocked(tmp_path):
    result = run_results_only_backtest(tmp_path)
    assert result["data_blocked_count"] < result["matches_evaluated"]
    assert result["model_ran_count"] > 0

