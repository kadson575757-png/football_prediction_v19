import pandas as pd

from football_prediction_v19.analysis.v2116_team_strength_filtered_pattern_test import add_strength_snapshots, analyze_match_strategy, compute_strategy_summary
from scripts.analyze_v2112_exact_scoreline_pattern_test import _prepare_matches


def test_v2116_result_direction_distribution_and_hit_excludes_blocked():
    fixtures = pd.DataFrame([
        {"match_date": "2025-08-01", "home_team": "A", "away_team": "B", "actual_home_goals": 2, "actual_away_goals": 0},
        {"match_date": "2025-08-02", "home_team": "C", "away_team": "D", "actual_home_goals": 0, "actual_away_goals": 1},
        {"match_date": "2025-08-08", "home_team": "A", "away_team": "C", "actual_home_goals": 1, "actual_away_goals": 0},
        {"match_date": "2025-08-09", "home_team": "B", "away_team": "D", "actual_home_goals": 2, "actual_away_goals": 0},
        {"match_date": "2025-08-16", "home_team": "A", "away_team": "D", "actual_home_goals": 1, "actual_away_goals": 1},
    ])
    matches = add_strength_snapshots(_prepare_matches(fixtures, "Premier League", "2025/26"), min_strength_matches=1)
    rows = pd.DataFrame([analyze_match_strategy(matches, 4, "BASELINE_UNFILTERED")])
    summary = compute_strategy_summary(rows)
    assert int(summary.loc[0, "result_evaluable_count"]) in {0, 1}
    assert "home_precision" in summary.columns
    assert "draw_recall" in summary.columns
