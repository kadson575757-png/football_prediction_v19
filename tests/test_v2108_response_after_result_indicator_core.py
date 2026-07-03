import pandas as pd

from football_prediction_v19.analysis.v2108_response_after_result_indicator import build_response_after_result_indicator


def test_response_after_result_uses_previous_result_sequences(monkeypatch):
    rows = pd.DataFrame([
        {"match_date": "2026-01-01", "home_team": "Arsenal", "away_team": "A", "home_goals": 0, "away_goals": 1},
        {"match_date": "2026-01-02", "home_team": "B", "away_team": "Arsenal", "home_goals": 0, "away_goals": 2},
        {"match_date": "2026-01-03", "home_team": "Arsenal", "away_team": "C", "home_goals": 1, "away_goals": 0},
        {"match_date": "2026-01-04", "home_team": "D", "away_team": "Arsenal", "home_goals": 2, "away_goals": 0},
        {"match_date": "2026-01-05", "home_team": "Arsenal", "away_team": "E", "home_goals": 3, "away_goals": 0},
        {"match_date": "2026-01-01", "home_team": "Chelsea", "away_team": "F", "home_goals": 1, "away_goals": 0},
        {"match_date": "2026-01-02", "home_team": "G", "away_team": "Chelsea", "home_goals": 1, "away_goals": 1},
        {"match_date": "2026-01-03", "home_team": "Chelsea", "away_team": "H", "home_goals": 1, "away_goals": 0},
        {"match_date": "2026-01-04", "home_team": "I", "away_team": "Chelsea", "home_goals": 2, "away_goals": 2},
        {"match_date": "2026-01-05", "home_team": "Chelsea", "away_team": "J", "home_goals": 0, "away_goals": 1},
        {"match_date": "2026-02-01", "home_team": "Arsenal", "away_team": "Chelsea", "home_goals": 0, "away_goals": 9},
    ])
    monkeypatch.setattr("football_prediction_v19.analysis.v2108_response_after_result_indicator._load_match_rows", lambda *args, **kwargs: rows)

    result = build_response_after_result_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-02-01", 0.4, 0.3, 0.3)

    assert result["rar_home_previous_result"] == "W"
    assert result["rar_away_previous_result"] == "L"
    assert result["rar_home_points_after_previous_result_type"] >= 0
    assert result["rar_away_ppg_after_previous_result_type"] >= 0.0
