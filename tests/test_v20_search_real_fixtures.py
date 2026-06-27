from scripts.search_v20_real_fixtures import run_search_v20_real_fixtures


def test_search_real_fixtures_mock_outputs(tmp_path):
    result = run_search_v20_real_fixtures(competition="Demo League", season="2025/26", team="Demo Home", opponent="Demo Away", date_from="2025-08-01", date_to="2025-08-31", output_dir=tmp_path, mock_data_dir="tests/fixtures/v20_one_command_runner")
    assert result["fixture_search_status"] == "READY"
    assert result["matches_found"] >= 1
    assert (tmp_path / "fixture_search_results.csv").exists()
