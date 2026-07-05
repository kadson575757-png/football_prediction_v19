import pandas as pd

from football_prediction_v19.analysis.v2116_team_strength_filtered_pattern_test import analyze_team_strength_filtered_patterns


def test_v2116_team_strength_filtered_safety_flags_false(tmp_path):
    fixtures = pd.DataFrame([
        {"match_date": "2025-08-01", "home_team": "A", "away_team": "B", "actual_home_goals": 2, "actual_away_goals": 0},
        {"match_date": "2025-08-02", "home_team": "C", "away_team": "D", "actual_home_goals": 0, "actual_away_goals": 1},
        {"match_date": "2025-08-08", "home_team": "A", "away_team": "C", "actual_home_goals": 1, "actual_away_goals": 0},
        {"match_date": "2025-08-09", "home_team": "B", "away_team": "D", "actual_home_goals": 2, "actual_away_goals": 0},
        {"match_date": "2025-08-16", "home_team": "A", "away_team": "D", "actual_home_goals": 1, "actual_away_goals": 1},
    ])
    result = analyze_team_strength_filtered_patterns(fixtures, output_dir=tmp_path, min_strength_matches=1)
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
    assert (tmp_path / "v2116_team_strength_summary.json").exists()
