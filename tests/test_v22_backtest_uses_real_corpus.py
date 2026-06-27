from football_prediction_v19.analysis.v21_winner_backtest import run_v21_winner_backtest
from football_prediction_v19.analysis.v22_real_season_corpus import build_real_season_corpus
from tests.v22_test_helpers import make_mock_source_dir


def test_v22_backtest_uses_real_corpus(tmp_path):
    mock_source = make_mock_source_dir(tmp_path)
    corpus = build_real_season_corpus(
        competition="Premier League",
        season="2025/26",
        output_dir=tmp_path / "corpus",
        mock_data_dir=str(mock_source),
    )
    result = run_v21_winner_backtest(
        None,
        tmp_path / "backtest",
        corpus_path=corpus["real_season_corpus_csv_path"],
        mock_data_dir=str(mock_source),
        min_matches_required=2,
    )
    assert result["matches_available"] >= 2
    assert result["corpus_status"] == "READY"
    assert result["fallback_data_used"] is False
