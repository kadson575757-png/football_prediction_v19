from football_prediction_v19.analysis.v202_real_no_odds_quality_gate import run_v202_real_no_odds_quality_gate


def test_v202_real_no_odds_quality_gate(tmp_path):
    result = run_v202_real_no_odds_quality_gate(tmp_path)
    assert result["v202_real_no_odds_quality_gate_status"] == "V202_READY_TO_TAG"
    assert result["recommendation"] == "V202_READY_TO_TAG"
