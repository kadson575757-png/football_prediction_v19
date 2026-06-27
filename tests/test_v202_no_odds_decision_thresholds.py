from football_prediction_v19.analysis.v20_tip_decision_engine import run_tip_decision_engine


def test_v202_no_odds_decision_thresholds(tmp_path):
    features = {"data_quality_score": 0.7, "xg_available": True, "odds_available": False, "source_quality_band": "MEDIUM"}
    model = {"model_status": "MODEL_READY", "model_confidence": 0.68, "model_risk_score": 0.3, "home_win_probability": 0.6, "draw_probability": 0.25, "away_win_probability": 0.15, "missing_inputs": ["odds"]}
    result = run_tip_decision_engine(model, "ASOF_PARTIAL", features, tmp_path)
    assert result["decision_class"] == "MODEL_TIP"
