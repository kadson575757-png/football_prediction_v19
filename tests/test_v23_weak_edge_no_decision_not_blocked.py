from football_prediction_v19.analysis.v21_winner_decision_policy import apply_winner_decision_policy


def test_v23_weak_edge_no_decision_not_blocked(tmp_path):
    decision = apply_winner_decision_policy({"model_status": "WINNER_MODEL_PARTIAL", "home_win_probability": 0.34, "draw_probability": 0.33, "away_win_probability": 0.33, "confidence": 0.45, "missing_inputs": ["xg"]}, {"eligibility_class": "LEAN_ONLY"}, {"source_quality_band": "MEDIUM"}, tmp_path)
    assert decision["decision_class"] in {"NO_DECISION", "NO_CLEAR_WINNER"}

