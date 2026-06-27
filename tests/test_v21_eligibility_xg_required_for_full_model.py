from football_prediction_v19.analysis.v21_prediction_eligibility import evaluate_prediction_eligibility


def test_v21_eligibility_xg_required_for_full_model():
    result = evaluate_prediction_eligibility({"status": "RESOLVED"}, {"prediction_tier": "TIER_1_FULL_XG", "table_available": True, "xg_available": False, "odds_available": False}, {"leakage_status": "CLEAN"})
    assert result["eligibility_class"] == "LEAN_ONLY"
