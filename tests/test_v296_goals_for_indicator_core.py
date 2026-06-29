import pandas as pd

from football_prediction_v19.analysis import v296_goals_for_indicator as mod


def test_v296_goals_for_per_match_and_no_leakage(monkeypatch):
    rows = pd.DataFrame(
        [
            {"match_date": "2026-03-01", "home_team": "Arsenal", "away_team": "Team X", "home_goals": 9, "away_goals": 0},
            {"match_date": "2026-03-02", "home_team": "Chelsea", "away_team": "Team Y", "home_goals": 9, "away_goals": 0},
            {"match_date": "2026-02-20", "home_team": "Arsenal", "away_team": "Team A", "home_goals": 3, "away_goals": 0},
            {"match_date": "2026-02-10", "home_team": "Team B", "away_team": "Arsenal", "home_goals": 1, "away_goals": 2},
            {"match_date": "2026-02-01", "home_team": "Arsenal", "away_team": "Team C", "home_goals": 1, "away_goals": 1},
            {"match_date": "2026-02-19", "home_team": "Chelsea", "away_team": "Team D", "home_goals": 1, "away_goals": 0},
            {"match_date": "2026-02-09", "home_team": "Team E", "away_team": "Chelsea", "home_goals": 1, "away_goals": 1},
            {"match_date": "2026-01-31", "home_team": "Chelsea", "away_team": "Team F", "home_goals": 2, "away_goals": 0},
        ]
    )
    monkeypatch.setattr(mod, "_load_match_rows", lambda *args, **kwargs: rows)

    result = mod.build_goals_for_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-03-01")

    assert result["home_goals_for_before_match"] == 6
    assert result["away_goals_for_before_match"] == 4
    assert result["home_goals_for_per_match_before_match"] == 2.0
    assert result["away_goals_for_per_match_before_match"] == 1.3333
    assert result["goals_for_per_match_diff"] == 0.6667
    assert result["goals_for_indicator_quality"] == "PARTIAL"


def test_v296_games_on_or_after_match_date_are_excluded(monkeypatch):
    rows = pd.DataFrame(
        [
            {"match_date": "2026-03-01", "home_team": "Arsenal", "away_team": "Team A", "home_goals": 5, "away_goals": 0},
            {"match_date": "2026-02-20", "home_team": "Arsenal", "away_team": "Team B", "home_goals": 1, "away_goals": 0},
            {"match_date": "2026-02-20", "home_team": "Chelsea", "away_team": "Team C", "home_goals": 0, "away_goals": 1},
        ]
    )
    monkeypatch.setattr(mod, "_load_match_rows", lambda *args, **kwargs: rows)

    result = mod.build_goals_for_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-03-01")

    assert result["home_goals_for_before_match"] == 1
    assert result["away_goals_for_before_match"] == 0
    assert result["goals_for_indicator_quality"] == "LOW"
