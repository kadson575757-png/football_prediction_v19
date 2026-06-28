import pandas as pd

from football_prediction_v19.analysis.v26_fixture_date_resolver import resolve_fixture_date


def test_v26_resolver_falls_back_to_football_data_when_corpus_empty(monkeypatch, tmp_path):
    empty_corpus = tmp_path / "empty_corpus.csv"
    pd.DataFrame(columns=["competition", "season", "match_date", "home_team", "away_team"]).to_csv(empty_corpus, index=False)
    normalized = tmp_path / "football_data_live_normalized.csv"
    pd.DataFrame(
        [
            {"Date": "01/03/2026", "HomeTeam": "Arsenal", "AwayTeam": "Chelsea", "FTHG": "", "FTAG": "", "FTR": ""},
        ]
    ).to_csv(normalized, index=False)

    def fake_live_adapter(*args, **kwargs):
        assert kwargs["enable_network"] is True
        return {"football_data_live_status": "SUCCESS", "football_data_live_normalized_path": str(normalized)}

    monkeypatch.setattr("football_prediction_v19.analysis.v26_fixture_date_resolver.run_football_data_live_adapter", fake_live_adapter)
    result = resolve_fixture_date(
        "Premier League",
        "2025/26",
        "Arsenal",
        "Chelsea",
        corpus_path=empty_corpus,
        enable_network=True,
        cache_only=False,
    )

    assert result["resolver_status"] == "RESOLVED"
    assert result["match_date"] == "2026-03-01"
    assert result["source_used"] == "football_data"

