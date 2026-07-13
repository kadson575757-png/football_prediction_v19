import pandas as pd

from football_prediction_v19.analysis.v2124_pl_multi_season_robustness import evaluate_pl_multi_season_robustness


def _stable_rows(year):
    return pd.DataFrame([
        {"match_date": f"{year}-01-01", "as_of_date": f"{year-1}-12-31", "home_team": "A", "away_team": "B", "actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.45, "draw_probability": 0.30, "away_probability": 0.25, "probability_edge": 0.15},
        {"match_date": f"{year}-01-02", "as_of_date": f"{year}-01-01", "home_team": "C", "away_team": "D", "actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.45, "draw_probability": 0.30, "away_probability": 0.25, "probability_edge": 0.15},
    ])


def test_cross_season_stability_rules_detect_repeated_pattern(tmp_path):
    seasons = ["2023/24", "2024/25", "2025/26"]
    result = evaluate_pl_multi_season_robustness(
        {season: _stable_rows(2024 + index) for index, season in enumerate(seasons)},
        seasons=seasons,
        expected_fixture_count=2,
        output_dir=tmp_path,
    )
    assert result["seasons_evaluated"] == 3
    assert result["seasons_with_draw_never_top"] == 3
    assert result["seasons_with_home_top_actual_draw_as_biggest_error"] == 3
    assert result["stable_error_pattern"] is True
    assert result["recommendation"] == "MODEL_ERROR_PATTERN_STABLE"
