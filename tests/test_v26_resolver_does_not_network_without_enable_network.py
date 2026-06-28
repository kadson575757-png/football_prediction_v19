import pandas as pd

from football_prediction_v19.analysis.v26_fixture_date_resolver import resolve_fixture_date


def test_v26_resolver_does_not_network_without_enable_network(monkeypatch, tmp_path):
    empty_corpus = tmp_path / "empty_corpus.csv"
    pd.DataFrame(columns=["competition", "season", "match_date", "home_team", "away_team"]).to_csv(empty_corpus, index=False)

    def fail_live_adapter(*args, **kwargs):
        raise AssertionError("football-data fallback must not run without enable_network")

    monkeypatch.setattr("football_prediction_v19.analysis.v26_fixture_date_resolver.run_football_data_live_adapter", fail_live_adapter)
    result = resolve_fixture_date(
        "Premier League",
        "2025/26",
        "Arsenal",
        "Chelsea",
        corpus_path=empty_corpus,
        enable_network=False,
        cache_only=False,
    )

    assert result["resolver_status"] == "NOT_FOUND"
    assert "network fallback disabled" in result["reason"]

