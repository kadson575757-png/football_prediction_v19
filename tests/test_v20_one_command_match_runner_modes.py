from scripts.run_v20_match import run_v20_match


def test_one_command_match_runner_cache_only_mode(tmp_path):
    result = run_v20_match(home_team="Demo Home", away_team="Demo Away", competition="Demo League", season="2025/26", match_date="2026-02-14", cache_only=True, cache_dir=tmp_path / "cache", output_dir=tmp_path / "out", base_dir=".")
    assert result["network_calls_enabled"] is False
    assert result["v20_match_status"] == "BLOCKED"
