from football_prediction_v19.analysis.v21_winner_decision_policy import apply_winner_decision_policy


def test_v23_no_clear_winner_not_blocked(tmp_path):
    decision = apply_winner_decision_policy({"model_status": "WINNER_MODEL_READY", "home_win_probability": 0.35, "draw_probability": 0.34, "away_win_probability": 0.31, "confidence": 0.56, "missing_inputs": []}, {"eligibility_class": "WINNER_MODEL_READY"}, {"source_quality_band": "MEDIUM"}, tmp_path)
    assert decision["decision_class"] != "DATA_BLOCKED"

