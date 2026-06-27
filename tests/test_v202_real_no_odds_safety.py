from football_prediction_v19.analysis.v202_real_no_odds_quality_gate import run_v202_real_no_odds_quality_gate


def test_v202_real_no_odds_safety(tmp_path):
    result = run_v202_real_no_odds_quality_gate(tmp_path)
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
