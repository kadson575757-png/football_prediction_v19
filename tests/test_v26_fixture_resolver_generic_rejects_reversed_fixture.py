from football_prediction_v19.analysis.v26_fixture_date_resolver import resolve_fixture_date
from tests.v26_test_helpers import make_fixture_corpus


def test_v26_fixture_resolver_generic_rejects_reversed_fixture(tmp_path):
    corpus = make_fixture_corpus(tmp_path / "corpus.csv")
    result = resolve_fixture_date("Premier League", "2025/26", "Chelsea", "Arsenal", corpus_path=corpus)
    assert result["resolver_status"] == "NOT_FOUND"
    assert result["reversed_fixture_found"] is True

