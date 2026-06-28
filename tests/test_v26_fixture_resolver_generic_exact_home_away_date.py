from football_prediction_v19.analysis.v26_fixture_date_resolver import resolve_fixture_date
from tests.v26_test_helpers import make_fixture_corpus


def test_v26_fixture_resolver_generic_exact_home_away_date(tmp_path):
    corpus = make_fixture_corpus(tmp_path / "corpus.csv")
    result = resolve_fixture_date("Premier League", "2025/26", "Arsenal", "Chelsea", corpus_path=corpus)
    assert result["resolver_status"] == "RESOLVED"
    assert result["match_date"] == "2026-03-01"

