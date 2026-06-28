from tests.v23_test_helpers import make_results_only_corpus
from football_prediction_v19.analysis.v21_winner_backtest import run_v21_winner_backtest


def test_v24_backtest_recommends_corpus_warm_when_insufficient(tmp_path):
    corpus = make_results_only_corpus(tmp_path / "corpus.csv", n=4)
    result = run_v21_winner_backtest(None, tmp_path / "out", corpus_path=corpus, min_matches_required=50)
    assert result["recommendation"] == "BUILD_OR_WARM_V22_CORPUS"

