from football_prediction_v19.analysis.v20_tip_decision_engine import run_tip_decision_engine


def test_decision_policy_no_bet_on_low_coverage_and_no_stake_roi(tmp_path):
    model = {"model_status": "MODEL_PARTIAL", "model_confidence": 0.55, "model_risk_score": 0.45, "missing_inputs": ["odds"], "home_win_probability": 0.4, "draw_probability": 0.3, "away_win_probability": 0.3}
    decision = run_tip_decision_engine(model, "ASOF_PARTIAL", {"data_quality_score": 0.66, "table_available": True, "xg_available": True, "odds_available": False}, tmp_path)
    assert decision["decision_class"] == "NO_BET"
    assert decision["automatic_betting_enabled"] is False
    assert decision["staking_logic_enabled"] is False
    assert decision["roi_logic_enabled"] is False
