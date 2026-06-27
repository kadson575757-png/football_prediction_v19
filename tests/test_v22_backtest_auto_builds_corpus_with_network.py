from football_prediction_v19.analysis.v21_winner_backtest import run_v21_winner_backtest
from tests.v22_test_helpers import make_mock_source_dir


def test_v22_backtest_auto_builds_corpus_with_network(tmp_path):
    result = run_v21_winner_backtest(
        None,
        tmp_path / "out",
        competition="Premier League",
        season="2025/26",
        mock_data_dir=str(make_mock_source_dir(tmp_path)),
        enable_network=True,
        min_matches_required=2,
    )
    assert result["matches_available"] >= 2
    assert result["corpus_status"] == "READY"
    assert result["fallback_data_used"] is True

