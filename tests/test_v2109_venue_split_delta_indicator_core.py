import pandas as pd

from football_prediction_v19.analysis.v2109_venue_split_delta_indicator import build_venue_split_delta_indicator


def test_venue_split_delta_rates_and_deltas(monkeypatch):
    rows = pd.DataFrame([
        {"match_date": "2026-01-01", "home_team": "Arsenal", "away_team": "A", "home_goals": 3, "away_goals": 0},
        {"match_date": "2026-01-02", "home_team": "B", "away_team": "Arsenal", "home_goals": 2, "away_goals": 0},
        {"match_date": "2026-01-03", "home_team": "Arsenal", "away_team": "C", "home_goals": 2, "away_goals": 1},
        {"match_date": "2026-01-04", "home_team": "Chelsea", "away_team": "D", "home_goals": 2, "away_goals": 0},
        {"match_date": "2026-01-05", "home_team": "E", "away_team": "Chelsea", "home_goals": 2, "away_goals": 0},
        {"match_date": "2026-01-06", "home_team": "F", "away_team": "Chelsea", "home_goals": 1, "away_goals": 1},
        {"match_date": "2026-02-01", "home_team": "Arsenal", "away_team": "Chelsea", "home_goals": 0, "away_goals": 9},
    ])
    monkeypatch.setattr("football_prediction_v19.analysis.v2109_venue_split_delta_indicator._load_match_rows", lambda *args, **kwargs: rows)

    result = build_venue_split_delta_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-02-01", 0.4, 0.3, 0.3)

    assert result["vsd_home_home_ppg"] == 3.0
    assert result["vsd_home_overall_ppg"] == 2.0
    assert result["vsd_home_venue_ppg_delta"] == 1.0
    assert result["vsd_away_away_ppg"] == 0.5
    assert "vsd_venue_split_signal" in result
