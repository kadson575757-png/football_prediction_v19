from scripts.run_v20_real_match_validation_batch import run_v20_real_match_validation_batch


def test_real_match_validation_batch_isolates_matches(tmp_path):
    result = run_v20_real_match_validation_batch("tests/fixtures/v20_real_match_autopilot/validation_matches_mock.yaml", tmp_path, mock_data_dir="tests/fixtures/v20_real_match_autopilot", base_dir=".")
    assert result["v20_real_match_validation_batch_status"] == "READY"
    assert result["matches_total"] == 1
    assert (tmp_path / "v20_real_match_validation_batch_results.csv").exists()
