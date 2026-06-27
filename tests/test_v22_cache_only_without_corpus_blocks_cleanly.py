from football_prediction_v19.analysis.v21_winner_backtest import run_v21_winner_backtest


def test_v22_cache_only_without_corpus_blocks_cleanly(tmp_path):
    result = run_v21_winner_backtest(
        None,
        tmp_path / "out",
        competition="Premier League",
        season="2099/00",
        cache_only=True,
        min_matches_required=2,
    )
    assert result["v21_winner_backtest_status"] == "BLOCKED"
    assert result["corpus_status"] == "EMPTY"
    assert result["matches_available"] == 0
    assert result["fallback_data_used"] is False

