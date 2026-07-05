import pandas as pd

from football_prediction_v19.analysis.v2118_draw_signal_discovery import compute_all_signal_groups, prepare_signal_rows


def test_v2118_draw_signal_grouping_core():
    rows = pd.DataFrame([
        {"actual_result": "DRAW", "home_win_probability": 0.34, "draw_probability": 0.30, "away_win_probability": 0.33, "probability_edge": 0.02},
        {"actual_result": "HOME", "home_win_probability": 0.50, "draw_probability": 0.25, "away_win_probability": 0.25, "probability_edge": 0.25},
    ])
    prepared = prepare_signal_rows(rows)
    groups = compute_all_signal_groups(prepared, min_sample=20)
    edge_group = groups[(groups["signal_name"].eq("probability_edge_signal")) & (groups["signal_group"].eq("EDGE_0_3"))].iloc[0]
    assert edge_group["count"] == 1
    assert edge_group["draw_count"] == 1
    assert edge_group["draw_rate"] == 1.0
    assert bool(edge_group["low_sample"]) is True
