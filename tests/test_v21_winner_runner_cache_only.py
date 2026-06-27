from scripts.run_v21_predict_winner import run_v21_predict_winner


def test_v21_winner_runner_cache_only(tmp_path):
    cache = tmp_path / "cache"
    run_v21_predict_winner(home_team="Demo Home", away_team="Demo Away", competition="Premier League", season="2025/26", match_date="2026-02-15", mock_data_dir="tests/fixtures/v20_live_source_adapters", cache_dir=str(cache), output_dir=tmp_path / "first")
    result = run_v21_predict_winner(home_team="Demo Home", away_team="Demo Away", competition="Premier League", season="2025/26", match_date="2026-02-15", cache_only=True, cache_dir=str(cache), output_dir=tmp_path / "second")
    assert result["cache_used"] is True
    assert result["network_calls_enabled"] is False
