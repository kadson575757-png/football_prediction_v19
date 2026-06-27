from football_prediction_v19.analysis.v20_tip_decision_engine import run_tip_decision_engine


def test_real_source_low_quality_decision_no_bet(tmp_path):
    decision = run_tip_decision_engine({"model_status": "MODEL_PARTIAL", "model_confidence": 0.5, "model_risk_score": 0.6, "missing_inputs": ["xg"]}, "ASOF_PARTIAL", {"data_quality_score": 0.45, "table_available": True, "xg_available": False, "odds_available": True}, tmp_path)
    assert decision["decision_class"] == "NO_BET"
    assert decision["staking_logic_enabled"] is False
