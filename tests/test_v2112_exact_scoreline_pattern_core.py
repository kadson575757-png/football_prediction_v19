import pandas as pd

from scripts.analyze_v2112_exact_scoreline_pattern_test import team_scoreline_pattern


def test_v2112_pattern_from_team_perspective():
    assert team_scoreline_pattern(pd.Series({"home_team": "Arsenal", "away_team": "Chelsea", "actual_home_goals": 3, "actual_away_goals": 1}), "Arsenal")["pattern"] == "W 3:1"
    assert team_scoreline_pattern(pd.Series({"home_team": "Chelsea", "away_team": "Arsenal", "actual_home_goals": 1, "actual_away_goals": 3}), "Arsenal")["pattern"] == "W 3:1"
    assert team_scoreline_pattern(pd.Series({"home_team": "Arsenal", "away_team": "Chelsea", "actual_home_goals": 1, "actual_away_goals": 3}), "Arsenal")["pattern"] == "L 1:3"
    assert team_scoreline_pattern(pd.Series({"home_team": "Chelsea", "away_team": "Arsenal", "actual_home_goals": 3, "actual_away_goals": 1}), "Arsenal")["pattern"] == "L 1:3"
    assert team_scoreline_pattern(pd.Series({"home_team": "Arsenal", "away_team": "Chelsea", "actual_home_goals": 2, "actual_away_goals": 2}), "Arsenal")["pattern"] == "D 2:2"

