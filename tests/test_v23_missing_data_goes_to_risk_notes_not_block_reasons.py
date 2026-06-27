from football_prediction_v19.analysis.v21_winner_decision_policy import apply_winner_decision_policy


def test_v23_missing_data_goes_to_risk_notes_not_block_reasons(tmp_path):
    decision = apply_winner_decision_policy({"model_status": "WINNER_MODEL_PARTIAL", "home_win_probability": 0.4, "draw_probability": 0.32, "away_win_probability": 0.28, "confidence": 0.56, "missing_inputs": ["xg", "odds"]}, {"eligibility_class": "LEAN_ONLY"}, {"source_quality_band": "MEDIUM"}, tmp_path)
    assert "xg" in decision["missing_data"]
    assert "block_reasons" not in decision

