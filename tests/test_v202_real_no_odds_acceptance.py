from football_prediction_v19.analysis.v202_real_no_odds_quality_gate import run_v202_real_no_odds_quality_gate


def test_v202_real_no_odds_acceptance(tmp_path):
    result = run_v202_real_no_odds_quality_gate(tmp_path)
    assert result["understat_parse_status"] == "PASSED"
    assert result["xg_bridge_status"] == "PASSED"
    assert result["no_odds_policy_status"] == "PASSED"
