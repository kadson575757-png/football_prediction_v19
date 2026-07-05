import pandas as pd

from football_prediction_v19.analysis.v2116_team_strength_filtered_pattern_test import compute_team_strength_before_match


def test_v2116_strength_score_uses_only_prior_matches_and_quality():
    prior = pd.DataFrame([
        {"match_date": "2025-08-01", "home_team": "Arsenal", "away_team": "A", "actual_home_goals": 2, "actual_away_goals": 0},
        {"match_date": "2025-08-08", "home_team": "B", "away_team": "Arsenal", "actual_home_goals": 1, "actual_away_goals": 1},
        {"match_date": "2025-08-15", "home_team": "Arsenal", "away_team": "C", "actual_home_goals": 0, "actual_away_goals": 1},
    ])
    stats = compute_team_strength_before_match(prior, "Arsenal", min_strength_matches=3)
    assert stats["matches_played_before_match"] == 3
    assert stats["points_before_match"] == 4
    assert stats["ppg_before_match"] == round(4 / 3, 4)
    assert stats["goal_difference_per_match_before_match"] == round(1 / 3, 4)
    assert stats["strength_score_before_match"] == round(round(4 / 3, 4) + round(1 / 3, 4) * 0.35, 4)
    assert stats["strength_quality"] == "READY"

    low = compute_team_strength_before_match(prior.head(2), "Arsenal", min_strength_matches=3)
    assert low["strength_quality"] == "LOW"
