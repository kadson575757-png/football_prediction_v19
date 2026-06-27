from football_prediction_v19.analysis.v20_tip_decision_engine import run_tip_decision_engine


def test_decision_confidence_thresholds_low_confidence_no_bet_or_lean(tmp_path):
    result = run_tip_decision_engine({"model_status": "MODEL_PARTIAL", "model_confidence": 0.5, "model_risk_score": 0.5, "missing_inputs": ["odds"]}, "ASOF_PARTIAL", {"data_quality_score": 0.66, "table_available": True, "xg_available": True, "odds_available": False}, tmp_path)
    assert result["decision_class"] == "NO_BET"
