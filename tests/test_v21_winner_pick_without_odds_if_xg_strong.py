from football_prediction_v19.analysis.v21_winner_decision_policy import apply_winner_decision_policy


def test_v21_winner_pick_without_odds_if_xg_strong(tmp_path):
    model = {"model_status": "WINNER_MODEL_READY", "home_win_probability": 0.58, "draw_probability": 0.24, "away_win_probability": 0.18, "predicted_winner": "HOME", "winner_team": "Arsenal", "confidence": 0.72}
    result = apply_winner_decision_policy(model, {"eligibility_class": "WINNER_MODEL_READY"}, {"source_quality_band": "MEDIUM", "odds_missing": True, "xg_missing": False}, tmp_path)
    assert result["decision_class"] == "WINNER_PICK"
    assert result["staking_logic_enabled"] is False
