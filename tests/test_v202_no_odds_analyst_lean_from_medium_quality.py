from football_prediction_v19.analysis.v20_tip_decision_engine import run_tip_decision_engine


def test_v202_no_odds_analyst_lean_from_medium_quality(tmp_path):
    features = {"data_quality_score": 0.65, "xg_available": True, "odds_available": False, "source_quality_band": "MEDIUM"}
    model = {"model_status": "MODEL_READY", "model_confidence": 0.56, "model_risk_score": 0.44, "home_win_probability": 0.54, "draw_probability": 0.28, "away_win_probability": 0.18, "missing_inputs": ["odds"]}
    result = run_tip_decision_engine(model, "ASOF_PARTIAL", features, tmp_path)
    assert result["decision_class"] == "ANALYST_LEAN"
