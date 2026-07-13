import pandas as pd

from football_prediction_v19.analysis.v2124_pl_multi_season_robustness import compute_season_metrics, prepare_season_rows


def test_season_metrics_cover_hits_brier_draw_and_confidence():
    rows = pd.DataFrame([
        {"match_date": "2024-01-01", "as_of_date": "2023-12-31", "home_team": "A", "away_team": "B", "actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.50, "draw_probability": 0.30, "away_probability": 0.20, "probability_edge": 0.20},
        {"match_date": "2024-01-02", "as_of_date": "2024-01-01", "home_team": "C", "away_team": "D", "actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.46, "draw_probability": 0.32, "away_probability": 0.22, "probability_edge": 0.14},
        {"match_date": "2024-01-03", "as_of_date": "2024-01-02", "home_team": "E", "away_team": "F", "actual_result": "AWAY", "top_probability_outcome": "AWAY", "home_win_probability": 0.25, "draw_probability": 0.30, "away_probability": 0.45, "probability_edge": 0.15},
    ])
    prepared = prepare_season_rows(rows, "2023/24")
    metrics = compute_season_metrics(prepared, "2023/24", expected_fixture_count=3)
    assert metrics["season_status"] == "READY"
    assert metrics["top_probability_hit_count"] == 2
    assert metrics["top_probability_miss_count"] == 1
    assert metrics["top_probability_hit_rate"] == 0.6667
    assert metrics["draw_top_count"] == 0
    assert metrics["actual_draw_count"] == 1
    assert metrics["wrong_high_confidence_count"] == 1
    assert metrics["multiclass_brier_score"] > 0
