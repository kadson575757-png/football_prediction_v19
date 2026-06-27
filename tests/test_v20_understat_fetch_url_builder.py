from football_prediction_v19.analysis.v20_understat_live_adapter import build_understat_league_url, normalize_understat_matches


def test_understat_url_builder_and_mock_parse():
    assert build_understat_league_url("EPL", "2025") == "https://understat.com/league/EPL/2025"
    df = normalize_understat_matches({"matches": [{"date": "2026-02-14", "home_team": "Arsenal", "away_team": "Chelsea", "home_xg": 1.2, "away_xg": 0.8}]})
    assert len(df) == 1
    assert df.iloc[0]["home_team"] == "Arsenal"
