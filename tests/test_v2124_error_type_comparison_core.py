import pandas as pd

from football_prediction_v19.analysis.v2124_pl_multi_season_robustness import compute_error_type_by_season, prepare_season_rows


def test_error_types_are_compared_per_season():
    first = prepare_season_rows(pd.DataFrame([
        {"actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.45, "draw_probability": 0.30, "away_probability": 0.25},
    ]), "2023/24")
    second = prepare_season_rows(pd.DataFrame([
        {"actual_result": "HOME", "top_probability_outcome": "AWAY", "home_win_probability": 0.30, "draw_probability": 0.30, "away_probability": 0.40},
    ]), "2024/25")
    summary = compute_error_type_by_season(pd.concat([first, second]), ["2023/24", "2024/25"])
    indexed = summary.set_index(["season", "error_type"])
    assert indexed.loc[("2023/24", "HOME_TOP_ACTUAL_DRAW"), "count"] == 1
    assert indexed.loc[("2024/25", "AWAY_TOP_ACTUAL_HOME"), "count"] == 1
