from scripts.debug_v20_real_match_sources import run_debug_v20_real_match_sources


def test_debug_real_match_sources_writes_debug_artifacts(tmp_path):
    result = run_debug_v20_real_match_sources(home_team="Unknown Home", away_team="Unknown Away", competition="Demo League", season="2025/26", match_date="2026-02-14", mock_data_dir="tests/fixtures/v20_one_command_runner", output_dir=tmp_path, base_dir=".")
    assert result["v20_real_source_debug_status"] == "BLOCKED"
    assert result["main_block_reason"] == "fixture_not_found"
    for name in ["debug_source_summary.md", "debug_source_summary.json", "debug_cache_summary.md", "debug_fixture_resolution.md", "debug_block_reason.md"]:
        assert (tmp_path / name).exists()
