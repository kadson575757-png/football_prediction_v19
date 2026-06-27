from football_prediction_v19.analysis.v20_tip_decision_engine import run_tip_decision_engine


def test_model_policy_conflict_gate_no_bet(tmp_path):
    result = run_tip_decision_engine({"model_status": "MODEL_READY", "model_confidence": 0.8, "model_risk_score": 0.2}, "ASOF_READY", {"data_quality_score": 1, "xg_available": True, "odds_available": True, "source_conflict_high": True}, tmp_path)
    assert result["decision_class"] == "NO_BET"
