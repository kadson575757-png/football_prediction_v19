from football_prediction_v19.analysis.v26_fixture_date_resolver import resolve_fixture_date
from tests.v26_test_helpers import make_fixture_corpus


def test_v26_fixture_resolver_generic_ambiguous_candidates(tmp_path):
    corpus = make_fixture_corpus(tmp_path / "corpus.csv", [{"match_date": "2026-03-01", "home_team": "Arsenal", "away_team": "Chelsea"}, {"match_date": "2026-04-01", "home_team": "Arsenal", "away_team": "Chelsea"}])
    result = resolve_fixture_date("Premier League", "2025/26", "Arsenal", "Chelsea", corpus_path=corpus)
    assert result["resolver_status"] == "AMBIGUOUS"
    assert result["candidates_count"] == 2

