from football_prediction_v19.analysis.v26_fixture_date_resolver import resolve_fixture_date
from tests.v26_test_helpers import make_fixture_corpus


def test_v26_known_fixture_regression_arsenal_chelsea(tmp_path):
    corpus = make_fixture_corpus(tmp_path / "corpus.csv")
    result = resolve_fixture_date("Premier League", "2025/26", "Arsenal", "Chelsea", corpus_path=corpus)
    assert result["match_date"] == "2026-03-01"

