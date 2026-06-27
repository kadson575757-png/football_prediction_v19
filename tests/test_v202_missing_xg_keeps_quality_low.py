from football_prediction_v19.analysis.v20_real_source_quality_score import compute_real_source_quality


def test_v202_missing_xg_keeps_quality_low(tmp_path):
    result = compute_real_source_quality("PARTIAL", {"table_available": True, "form_available": True, "xg_available": False, "odds_available": False}, "CLEAN", cache_used=True, output_dir=tmp_path)
    assert result["source_quality_band"] == "LOW"
