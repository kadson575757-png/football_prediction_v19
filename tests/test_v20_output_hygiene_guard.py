from football_prediction_v19.analysis.v20_output_hygiene_guard import run_v20_output_hygiene_guard


def test_output_hygiene_guard_passes_without_cache_dir(tmp_path):
    result = run_v20_output_hygiene_guard(tmp_path)
    assert result["output_hygiene_status"] == "PASSED"
