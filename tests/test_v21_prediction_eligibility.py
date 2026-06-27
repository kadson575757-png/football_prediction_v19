from football_prediction_v19.analysis.v21_prediction_eligibility import evaluate_prediction_eligibility


def test_v21_prediction_eligibility_ready(tmp_path):
    result = evaluate_prediction_eligibility({"status": "RESOLVED"}, {"prediction_tier": "TIER_1_FULL_XG", "table_available": True, "xg_available": True, "odds_available": False}, {"leakage_status": "CLEAN"}, tmp_path)
    assert result["eligibility_class"] == "WINNER_MODEL_READY"
