from football_prediction_v19.analysis.v20_real_source_quality_score import compute_real_source_quality


def test_real_source_quality_score_bands(tmp_path):
    high = compute_real_source_quality("RESOLVED", {"table_available": True, "form_available": True, "xg_available": True, "player_xg_available": True, "odds_available": True}, "CLEAN", True, output_dir=tmp_path)
    assert high["source_quality_band"] == "HIGH"
    low = compute_real_source_quality("NOT_FOUND", {"table_available": False}, "BLOCKED")
    assert low["source_quality_band"] == "BLOCKED"
