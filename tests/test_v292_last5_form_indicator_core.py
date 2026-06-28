import pandas as pd

from football_prediction_v19.analysis import v292_last5_form_indicator as mod


def test_v292_last5_points_and_no_leakage(monkeypatch):
    rows = pd.DataFrame(
        [
            {"match_date": "2026-02-28", "home_team": "Arsenal", "away_team": "Chelsea", "home_goals": 9, "away_goals": 0},
            {"match_date": "2026-02-20", "home_team": "Arsenal", "away_team": "Team A", "home_goals": 2, "away_goals": 0},
            {"match_date": "2026-02-10", "home_team": "Team B", "away_team": "Arsenal", "home_goals": 1, "away_goals": 1},
            {"match_date": "2026-02-01", "home_team": "Arsenal", "away_team": "Team C", "home_goals": 0, "away_goals": 1},
            {"match_date": "2026-01-20", "home_team": "Team D", "away_team": "Arsenal", "home_goals": 0, "away_goals": 3},
            {"match_date": "2026-01-10", "home_team": "Arsenal", "away_team": "Team E", "home_goals": 2, "away_goals": 2},
            {"match_date": "2026-02-21", "home_team": "Chelsea", "away_team": "Team F", "home_goals": 1, "away_goals": 0},
            {"match_date": "2026-02-11", "home_team": "Team G", "away_team": "Chelsea", "home_goals": 2, "away_goals": 0},
            {"match_date": "2026-02-02", "home_team": "Chelsea", "away_team": "Team H", "home_goals": 0, "away_goals": 0},
            {"match_date": "2026-01-21", "home_team": "Team I", "away_team": "Chelsea", "home_goals": 1, "away_goals": 3},
            {"match_date": "2026-01-11", "home_team": "Chelsea", "away_team": "Team J", "home_goals": 0, "away_goals": 2},
        ]
    )
    monkeypatch.setattr(mod, "_load_match_rows", lambda *args, **kwargs: rows)

    result = mod.build_last5_form_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-03-01")

    assert result["home_last5_points"] == 10
    assert result["away_last5_points"] == 7
    assert result["last5_points_diff"] == 3
    assert result["home_last5_matches_before_match"] == 5
    assert result["away_last5_matches_before_match"] == 5
    assert result["last5_indicator_quality"] == "FULL"


def test_v292_matches_on_or_after_match_date_are_excluded(monkeypatch):
    rows = pd.DataFrame(
        [
            {"match_date": "2026-03-01", "home_team": "Arsenal", "away_team": "Team A", "home_goals": 5, "away_goals": 0},
            {"match_date": "2026-03-02", "home_team": "Chelsea", "away_team": "Team B", "home_goals": 0, "away_goals": 5},
            {"match_date": "2026-02-20", "home_team": "Arsenal", "away_team": "Team C", "home_goals": 1, "away_goals": 0},
            {"match_date": "2026-02-20", "home_team": "Chelsea", "away_team": "Team D", "home_goals": 0, "away_goals": 1},
        ]
    )
    monkeypatch.setattr(mod, "_load_match_rows", lambda *args, **kwargs: rows)

    result = mod.build_last5_form_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-03-01")

    assert result["home_last5_points"] == 3
    assert result["away_last5_points"] == 0
    assert result["home_last5_matches_before_match"] == 1
    assert result["away_last5_matches_before_match"] == 1
    assert result["last5_indicator_quality"] == "LOW"
