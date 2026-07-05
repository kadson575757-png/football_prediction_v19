import pandas as pd

from scripts.evaluate_v2111_pl_2025_26_analysis_quality import attach_results, compute_quality_summary


def test_v2111_analysis_quality_metrics_core():
    analysis = pd.DataFrame([
        {"competition": "Premier League", "season": "2025/26", "match_date": "2025-08-16", "home_team": "Arsenal", "away_team": "Chelsea", "top_probability_outcome": "HOME", "home_win_probability": 0.5, "draw_probability": 0.25, "away_win_probability": 0.25},
        {"competition": "Premier League", "season": "2025/26", "match_date": "2025-08-17", "home_team": "Liverpool", "away_team": "Everton", "top_probability_outcome": "AWAY", "home_win_probability": 0.3, "draw_probability": 0.3, "away_win_probability": 0.4},
        {"competition": "Premier League", "season": "2025/26", "match_date": "2025-08-18", "home_team": "Spurs", "away_team": "Villa", "top_probability_outcome": "DRAW", "home_win_probability": 0.34, "draw_probability": 0.35, "away_win_probability": 0.31},
    ])
    results = pd.DataFrame([
        {"competition": "Premier League", "season": "2025/26", "match_date": "2025-08-16", "home_team": "Arsenal", "away_team": "Chelsea", "actual_home_goals": 2, "actual_away_goals": 1},
        {"competition": "Premier League", "season": "2025/26", "match_date": "2025-08-17", "home_team": "Liverpool", "away_team": "Everton", "actual_home_goals": 1, "actual_away_goals": 0},
    ])

    rows = attach_results(analysis, results)
    summary = compute_quality_summary(rows)

    assert summary["rows_loaded"] == 3
    assert summary["result_known_count"] == 2
    assert summary["result_unknown_count"] == 1
    assert summary["evaluatable_count"] == 2
    assert summary["top_probability_hit_count"] == 1
    assert summary["top_probability_miss_count"] == 1
    assert summary["top_probability_hit_rate"] == 0.5
    assert summary["home_prediction_count"] == 1
    assert summary["home_prediction_hit_count"] == 1
    assert summary["away_prediction_count"] == 1
    assert summary["away_prediction_hit_count"] == 0
    assert summary["actual_home_count"] == 2

