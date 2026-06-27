from scripts.run_v20_match import run_v20_match


def test_cache_used_false_explains_expected_path(tmp_path):
    result = run_v20_match(home_team="Demo Home", away_team="Demo Away", competition="Demo League", season="2025/26", match_date="2026-02-14", cache_only=True, cache_dir=tmp_path / "empty_cache", output_dir=tmp_path / "out", base_dir=".")
    assert result["cache_used"] is False
    assert "no_cache" in result["block_reasons"]
    football = result["source_status"]["football_data"]
    assert football["cache_lookup_attempted"] is True
    assert football["expected_cache_path"]
    assert result["network_calls_enabled"] is False
