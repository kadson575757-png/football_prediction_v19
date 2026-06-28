from football_prediction_v19.analysis.v26_fixture_date_resolver import resolve_fixture_date
from tests.v26_test_helpers import make_fixture_corpus


def test_v26_fixture_resolver_uses_team_aliases(tmp_path):
    corpus = make_fixture_corpus(tmp_path / "corpus.csv", [{"match_date": "2026-03-01", "home_team": "Manchester United", "away_team": "Chelsea"}])
    result = resolve_fixture_date("Premier League", "2025/26", "Man Utd", "Chelsea", corpus_path=corpus)
    assert result["resolver_status"] == "RESOLVED"
    assert result["alias_matched"] is True

