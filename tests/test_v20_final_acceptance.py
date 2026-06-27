from football_prediction_v19.analysis.v20_final_release_gate import run_v20_final_release_gate


def test_v20_final_acceptance(tmp_path):
    result = run_v20_final_release_gate(tmp_path, ".")
    assert result["real_match_autopilot_status"] == "PASSED"
    assert result["no_leakage_backtest_status"] == "PASSED"
    assert result["one_command_runner_status"] == "PASSED"
    assert result["automatic_betting_enabled"] is False
