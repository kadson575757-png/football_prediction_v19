from football_prediction_v19.analysis.v21_winner_decision_policy import apply_winner_decision_policy


def test_v23_results_only_can_produce_winner_lean(tmp_path):
    decision = apply_winner_decision_policy({"model_status": "WINNER_MODEL_PARTIAL", "predicted_winner": "HOME", "winner_team": "Home", "home_win_probability": 0.46, "draw_probability": 0.30, "away_win_probability": 0.24, "confidence": 0.60, "missing_inputs": ["xg", "odds"]}, {"eligibility_class": "LEAN_ONLY"}, {"source_quality_band": "MEDIUM", "league_prediction_tier": "TIER_2_RESULTS_ONLY", "xg_missing": True}, tmp_path)
    assert decision["decision_class"] == "WINNER_LEAN"

