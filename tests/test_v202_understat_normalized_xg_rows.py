from football_prediction_v19.analysis.v20_understat_live_adapter import normalize_understat_matches


def test_v202_understat_normalized_xg_rows():
    frame = normalize_understat_matches({"matches": [{"date": "2025-08-20", "home_team": "Arsenal", "away_team": "Leeds", "home_xg": "2.1", "away_xg": "0.6"}]})
    assert list(frame.columns)[:6] == ["id", "date", "home_team", "away_team", "home_xg", "away_xg"]
    assert frame.loc[0, "home_xg"] == 2.1
    assert frame.loc[0, "away_team"] == "Leeds United"
