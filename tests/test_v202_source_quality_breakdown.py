from football_prediction_v19.analysis.v20_real_source_quality_score import compute_real_source_quality


def test_v202_source_quality_breakdown(tmp_path):
    result = compute_real_source_quality("RESOLVED", {"table_available": True, "form_available": True, "xg_available": True, "odds_available": False}, "CLEAN", cache_used=True, output_dir=tmp_path)
    breakdown = result["source_quality_breakdown"]
    for key in ["fixture_score", "table_form_score", "xg_score", "odds_score", "cache_score", "leakage_score", "missing_data_penalty", "final_score", "final_band"]:
        assert key in breakdown
