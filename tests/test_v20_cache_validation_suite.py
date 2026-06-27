from football_prediction_v19.analysis.v20_cache_validation_suite import run_cache_validation_suite


def test_cache_validation_suite_missing_cache_blocks_without_crash(tmp_path):
    result = run_cache_validation_suite(tmp_path / "missing_cache", tmp_path / "out")
    assert result["v20_cache_validation_status"] == "BLOCKED"
    assert result["network_calls_enabled"] is False
    assert (tmp_path / "out" / "v20_cache_validation_results.json").exists()
