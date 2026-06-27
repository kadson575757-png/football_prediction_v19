from football_prediction_v19.analysis.v21_winner_decision_policy import apply_winner_decision_policy


def test_v21_winner_decision_policy(tmp_path):
    model = {"model_status": "WINNER_MODEL_READY", "home_win_probability": 0.56, "draw_probability": 0.25, "away_win_probability": 0.19, "predicted_winner": "HOME", "winner_team": "Arsenal", "confidence": 0.7}
    result = apply_winner_decision_policy(model, {"eligibility_class": "WINNER_MODEL_READY"}, {"source_quality_band": "MEDIUM"}, tmp_path)
    assert result["decision_class"] == "WINNER_PICK"
