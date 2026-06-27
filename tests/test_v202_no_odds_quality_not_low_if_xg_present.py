from football_prediction_v19.analysis.v20_real_source_quality_score import compute_real_source_quality


def test_v202_no_odds_quality_not_low_if_xg_present(tmp_path):
    result = compute_real_source_quality("RESOLVED", {"table_available": True, "form_available": True, "xg_available": True, "odds_available": False}, "CLEAN", cache_used=True, output_dir=tmp_path)
    assert result["source_quality_band"] in {"MEDIUM", "HIGH"}
