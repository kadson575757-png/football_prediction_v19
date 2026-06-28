from football_prediction_v19.analysis.v26_fixture_date_resolver import resolve_fixture_date
from tests.v26_test_helpers import make_fixture_corpus


def test_v26_known_fixture_regression_multiple_leagues(tmp_path):
    corpus = make_fixture_corpus(tmp_path / "corpus.csv")
    assert resolve_fixture_date("Bundesliga", "2025/26", "Bayern Munich", "Borussia Dortmund", corpus_path=corpus)["resolver_status"] == "RESOLVED"
    assert resolve_fixture_date("La Liga", "2025/26", "Barcelona", "Real Madrid", corpus_path=corpus)["resolver_status"] == "RESOLVED"

