import pandas as pd

from football_prediction_v19.analysis import v294_goal_difference_indicator as mod


def test_v294_goal_difference_and_no_leakage(monkeypatch):
    rows = pd.DataFrame(
        [
            {"match_date": "2026-03-01", "home_team": "Arsenal", "away_team": "Team X", "home_goals": 9, "away_goals": 0},
            {"match_date": "2026-03-02", "home_team": "Chelsea", "away_team": "Team Y", "home_goals": 0, "away_goals": 9},
            {"match_date": "2026-02-20", "home_team": "Arsenal", "away_team": "Team A", "home_goals": 3, "away_goals": 0},
            {"match_date": "2026-02-10", "home_team": "Team B", "away_team": "Arsenal", "home_goals": 1, "away_goals": 2},
            {"match_date": "2026-02-01", "home_team": "Chelsea", "away_team": "Team C", "home_goals": 1, "away_goals": 2},
            {"match_date": "2026-01-20", "home_team": "Team D", "away_team": "Chelsea", "home_goals": 3, "away_goals": 1},
            {"match_date": "2026-01-10", "home_team": "Arsenal", "away_team": "Chelsea", "home_goals": 2, "away_goals": 0},
        ]
    )
    monkeypatch.setattr(mod, "_load_match_rows", lambda *args, **kwargs: rows)

    result = mod.build_goal_difference_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-03-01")

    assert result["home_goals_for_before_match"] == 7
    assert result["home_goals_against_before_match"] == 1
    assert result["away_goals_for_before_match"] == 2
    assert result["away_goals_against_before_match"] == 7
    assert result["home_goal_difference_before_match"] == 6
    assert result["away_goal_difference_before_match"] == -5
    assert result["goal_difference_diff"] == 11
    assert result["home_matches_before_match"] == 3
    assert result["away_matches_before_match"] == 3
    assert result["goal_difference_indicator_quality"] == "PARTIAL"


def test_v294_games_on_or_after_match_date_are_excluded(monkeypatch):
    rows = pd.DataFrame(
        [
            {"match_date": "2026-03-01", "home_team": "Arsenal", "away_team": "Team A", "home_goals": 5, "away_goals": 0},
            {"match_date": "2026-02-20", "home_team": "Arsenal", "away_team": "Team B", "home_goals": 1, "away_goals": 0},
            {"match_date": "2026-02-20", "home_team": "Chelsea", "away_team": "Team C", "home_goals": 0, "away_goals": 1},
        ]
    )
    monkeypatch.setattr(mod, "_load_match_rows", lambda *args, **kwargs: rows)

    result = mod.build_goal_difference_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-03-01")

    assert result["home_goal_difference_before_match"] == 1
    assert result["away_goal_difference_before_match"] == -1
    assert result["goal_difference_diff"] == 2
    assert result["goal_difference_indicator_quality"] == "LOW"
