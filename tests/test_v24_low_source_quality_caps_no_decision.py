from football_prediction_v19.analysis.v21_winner_decision_policy import apply_winner_decision_policy


def test_v24_low_source_quality_caps_no_decision(tmp_path):
    decision = apply_winner_decision_policy({"model_status": "WINNER_MODEL_PARTIAL", "home_win_probability": 0.50, "draw_probability": 0.25, "away_win_probability": 0.25, "confidence": 0.60, "missing_inputs": ["xg"]}, {"eligibility_class": "LEAN_ONLY"}, {"source_quality_band": "LOW", "league_prediction_tier": "TIER_2_RESULTS_ONLY", "xg_missing": True}, tmp_path, "config/v24_winner_decision_policy.yaml")
    assert decision["decision_class"] == "NO_DECISION"

