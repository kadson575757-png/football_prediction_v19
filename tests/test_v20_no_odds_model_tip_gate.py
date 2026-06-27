from football_prediction_v19.analysis.v20_tip_decision_engine import run_tip_decision_engine


def test_model_tip_allowed_without_odds_when_confidence_is_clear(tmp_path):
    model = {
        "model_status": "MODEL_READY",
        "model_confidence": 0.8,
        "model_risk_score": 0.2,
        "home_win_probability": 0.62,
        "draw_probability": 0.22,
        "away_win_probability": 0.16,
        "missing_inputs": ["odds"],
    }
    features = {"data_quality_score": 0.74, "xg_available": True, "odds_available": False, "source_conflict_high": False}
    result = run_tip_decision_engine(model, "READY", features, tmp_path)
    assert result["decision_class"] == "MODEL_TIP"
    assert result["automatic_betting_enabled"] is False


def test_model_tip_downgrades_to_analyst_lean_without_odds_when_confidence_lower(tmp_path):
    model = {"model_status": "MODEL_READY", "model_confidence": 0.72, "model_risk_score": 0.3, "home_win_probability": 0.62, "draw_probability": 0.22, "away_win_probability": 0.16, "missing_inputs": ["odds"]}
    features = {"data_quality_score": 0.74, "xg_available": True, "odds_available": False, "source_conflict_high": False}
    result = run_tip_decision_engine(model, "READY", features, tmp_path)
    assert result["decision_class"] == "ANALYST_LEAN"
