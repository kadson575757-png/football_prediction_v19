def fake_core_result(decision_class="WINNER_LEAN", predicted_winner="HOME"):
    return {
        "decision_class": decision_class,
        "predicted_winner": predicted_winner,
        "winner_team": "Arsenal",
        "home_win_probability": 0.43,
        "draw_probability": 0.31,
        "away_win_probability": 0.26,
        "confidence": 0.56,
        "source_quality_band": "MEDIUM",
        "model_status": "WINNER_MODEL_PARTIAL",
        "eligibility_class": "LEAN_ONLY",
        "winner_model": {"missing_inputs": ["xg", "odds"], "main_edges": ["home form edge"], "main_risks": ["xG missing", "odds missing"]},
        "winner_decision": {},
    }
