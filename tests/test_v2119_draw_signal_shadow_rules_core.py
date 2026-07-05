import pandas as pd

from football_prediction_v19.analysis.v2119_draw_signal_shadow_probe import apply_shadow_strategy, prepare_shadow_rows, probability_edge_signal


def test_v2119_edge_signal_and_shadow_rules_core():
    assert probability_edge_signal(0.03) == "EDGE_0_3"
    assert probability_edge_signal(0.06) == "EDGE_3_6"
    assert probability_edge_signal(0.10) == "EDGE_6_10"
    assert probability_edge_signal(0.11) == "EDGE_GT_10"
    rows = prepare_shadow_rows(pd.DataFrame([
        {"actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.34, "draw_probability": 0.31, "away_win_probability": 0.30, "probability_edge": 0.05},
        {"actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.50, "draw_probability": 0.27, "away_win_probability": 0.23, "probability_edge": 0.02},
        {"actual_result": "DRAW", "top_probability_outcome": "AWAY", "home_win_probability": 0.31, "draw_probability": 0.30, "away_win_probability": 0.39, "probability_edge": 0.05},
    ]))
    assert apply_shadow_strategy(rows, "EDGE_3_6_DRAW_TOP")["shadow_top_outcome"].tolist() == ["DRAW", "HOME", "DRAW"]
    assert apply_shadow_strategy(rows, "EDGE_0_6_DRAW_TOP")["shadow_top_outcome"].tolist() == ["DRAW", "DRAW", "DRAW"]
    assert apply_shadow_strategy(rows, "EDGE_3_6_AND_DRAW_RANK_2")["shadow_top_outcome"].tolist() == ["DRAW", "HOME", "AWAY"]
    assert apply_shadow_strategy(rows, "EDGE_3_6_SOFT_MIX")["shadow_top_outcome"].tolist() == ["DRAW", "HOME", "AWAY"]
