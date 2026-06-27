from football_prediction_v19.analysis.v20_tip_decision_engine import run_tip_decision_engine


def test_v202_no_odds_no_model_tip_without_xg(tmp_path):
    features = {"data_quality_score": 0.7, "xg_available": False, "odds_available": False, "source_quality_band": "MEDIUM"}
    model = {"model_status": "MODEL_PARTIAL", "model_confidence": 0.8, "model_risk_score": 0.2, "home_win_probability": 0.7, "draw_probability": 0.2, "away_win_probability": 0.1, "missing_inputs": ["xg", "odds"]}
    result = run_tip_decision_engine(model, "ASOF_PARTIAL", features, tmp_path)
    assert result["decision_class"] != "MODEL_TIP"
