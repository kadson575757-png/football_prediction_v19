import pandas as pd

from football_prediction_v19.analysis.v26_fixture_date_resolver import resolve_fixture_date


def test_v26_resolver_reports_football_data_source_used(monkeypatch, tmp_path):
    empty_corpus = tmp_path / "empty_corpus.csv"
    pd.DataFrame(columns=["competition", "season", "match_date", "home_team", "away_team"]).to_csv(empty_corpus, index=False)
    normalized = tmp_path / "football_data_live_normalized.csv"
    pd.DataFrame(
        [
            {"Date": "2026-03-01", "HomeTeam": "Arsenal", "AwayTeam": "Chelsea", "FTHG": "", "FTAG": "", "FTR": ""},
        ]
    ).to_csv(normalized, index=False)

    monkeypatch.setattr(
        "football_prediction_v19.analysis.v26_fixture_date_resolver.run_football_data_live_adapter",
        lambda *args, **kwargs: {"football_data_live_status": "CACHE_HIT", "football_data_live_normalized_path": str(normalized)},
    )
    result = resolve_fixture_date(
        "Premier League",
        "2025/26",
        "Arsenal",
        "Chelsea",
        corpus_path=empty_corpus,
        enable_network=True,
        cache_only=False,
    )

    assert result["source_used"] == "football_data"
    assert result["reason"] == "Resolved exact home/away fixture from football-data live source"

