import pandas as pd

from football_prediction_v19.analysis.v2125_cross_season_edge_reliability import apply_shadow_configuration, prepare_probe_rows


def test_uniform_shrink_draw_lift_and_high_edge_sharpen():
    low = prepare_probe_rows(pd.DataFrame([{
        "season": "S1", "actual_result": "DRAW", "top_probability_outcome": "HOME",
        "home_win_probability": 0.40, "draw_probability": 0.32,
        "away_win_probability": 0.28, "probability_edge": 0.04,
    }]))
    shrink = apply_shadow_configuration(low, "LOW_EDGE_UNIFORM_SHRINK_010").iloc[0]
    assert shrink["shadow_home_win_probability"] < 0.40
    assert shrink["shadow_away_win_probability"] > 0.28
    lift = apply_shadow_configuration(low, "LOW_EDGE_DRAW_LIFT_010").iloc[0]
    assert lift["shadow_draw_probability"] == 0.33
    assert lift["shadow_home_win_probability"] < 0.40
    assert lift["shadow_away_win_probability"] < 0.28

    high = prepare_probe_rows(pd.DataFrame([{
        "season": "S1", "actual_result": "HOME", "top_probability_outcome": "HOME",
        "home_win_probability": 0.55, "draw_probability": 0.27,
        "away_win_probability": 0.18, "probability_edge": 0.28,
    }]))
    sharpen = apply_shadow_configuration(high, "HIGH_EDGE_SHARPEN_005").iloc[0]
    assert sharpen["shadow_home_win_probability"] == 0.555
    assert sharpen["adjustment_applied"]
