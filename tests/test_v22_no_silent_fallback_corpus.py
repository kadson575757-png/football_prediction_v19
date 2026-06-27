from football_prediction_v19.analysis.v21_winner_backtest import run_v21_winner_backtest


def test_v22_no_silent_fallback_corpus(tmp_path):
    result = run_v21_winner_backtest(
        None,
        tmp_path / "out",
        competition="Bundesliga",
        season="2099/00",
        cache_only=True,
    )
    assert result["matches_requested"] == 0
    assert result["matches_available"] == 0
    assert result["sample_warning"]
    assert result["v21_winner_backtest_status"] == "BLOCKED"

