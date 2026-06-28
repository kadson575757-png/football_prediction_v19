from football_prediction_v19.analysis.v26_fixture_date_resolver import resolve_fixture_date
from tests.v26_test_helpers import make_fixture_corpus


def test_v26_fixture_resolver_works_across_multiple_leagues(tmp_path):
    corpus = make_fixture_corpus(tmp_path / "corpus.csv")
    result = resolve_fixture_date("Bundesliga", "2025/26", "Bayern Munich", "Borussia Dortmund", corpus_path=corpus)
    assert result["resolver_status"] == "RESOLVED"
    assert result["match_date"] == "2026-04-12"
