import pandas as pd

from football_prediction_v19.analysis.v2118_draw_signal_discovery import compute_combo_groups, prepare_signal_rows


def test_v2118_draw_signal_combo_core():
    rows = pd.DataFrame([
        {"actual_result": "DRAW", "home_win_probability": 0.34, "draw_probability": 0.30, "away_win_probability": 0.33, "probability_edge": 0.02},
        {"actual_result": "AWAY", "home_win_probability": 0.25, "draw_probability": 0.28, "away_win_probability": 0.47, "probability_edge": 0.19},
    ])
    combos = compute_combo_groups(prepare_signal_rows(rows), min_sample=1)
    assert "EDGE_X_HA_SIMILARITY" in set(combos["signal_name"])
    assert int(combos["count"].sum()) > 0
