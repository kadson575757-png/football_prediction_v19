from football_prediction_v19.analysis.v21_winner_decision_policy import apply_winner_decision_policy


def test_v21_no_clear_winner_policy(tmp_path):
    model = {"model_status": "WINNER_MODEL_READY", "home_win_probability": 0.36, "draw_probability": 0.33, "away_win_probability": 0.31, "predicted_winner": "NO_CLEAR_WINNER", "confidence": 0.5}
    result = apply_winner_decision_policy(model, {"eligibility_class": "WINNER_MODEL_READY"}, {"source_quality_band": "MEDIUM"}, tmp_path)
    assert result["decision_class"] == "NO_CLEAR_WINNER"
