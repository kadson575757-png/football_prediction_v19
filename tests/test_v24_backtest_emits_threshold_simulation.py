from tests.v24_test_helpers import run_v24_backtest


def test_v24_backtest_emits_threshold_simulation(tmp_path):
    result = run_v24_backtest(tmp_path)
    assert result["threshold_simulation_status"] == "PASSED"
    assert "selected_policy_top1_accuracy_decisions_only" in result
