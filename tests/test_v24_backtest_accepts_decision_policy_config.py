from tests.v24_test_helpers import run_v24_backtest


def test_v24_backtest_accepts_decision_policy_config(tmp_path):
    result = run_v24_backtest(tmp_path)
    assert result["active_decision_policy"] == "balanced_results_only_safe"

