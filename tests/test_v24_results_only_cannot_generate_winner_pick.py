from football_prediction_v19.analysis.v21_winner_decision_policy import apply_winner_decision_policy


def test_v24_results_only_cannot_generate_winner_pick(tmp_path):
    decision = apply_winner_decision_policy({"model_status": "WINNER_MODEL_PARTIAL", "predicted_winner": "HOME", "winner_team": "A", "home_win_probability": 0.70, "draw_probability": 0.20, "away_win_probability": 0.10, "confidence": 0.62, "missing_inputs": ["xg"]}, {"eligibility_class": "LEAN_ONLY"}, {"source_quality_band": "MEDIUM", "league_prediction_tier": "TIER_2_RESULTS_ONLY", "xg_missing": True}, tmp_path, "config/v24_winner_decision_policy.yaml")
    assert decision["decision_class"] != "WINNER_PICK"

