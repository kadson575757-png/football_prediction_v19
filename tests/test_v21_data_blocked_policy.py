from football_prediction_v19.analysis.v21_winner_decision_policy import apply_winner_decision_policy


def test_v21_data_blocked_policy(tmp_path):
    result = apply_winner_decision_policy({"model_status": "WINNER_MODEL_BLOCKED"}, {"eligibility_class": "DATA_BLOCKED"}, {"source_quality_band": "LOW"}, tmp_path)
    assert result["decision_class"] == "DATA_BLOCKED"
