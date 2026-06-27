from tests.v23_test_helpers import make_results_only_corpus
from football_prediction_v19.analysis.v21_winner_backtest import run_v21_winner_backtest


def test_v23_backtest_reports_hard_vs_invalid_blocks(tmp_path):
    corpus = make_results_only_corpus(tmp_path / "corpus.csv", missing_result=True)
    result = run_v21_winner_backtest(None, tmp_path / "out", corpus_path=corpus, min_matches_required=2)
    assert "hard_data_blocked_count" in result
    assert "invalid_data_blocked_count" in result

