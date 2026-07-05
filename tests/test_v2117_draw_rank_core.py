import pandas as pd

from football_prediction_v19.analysis.v2117_draw_bias_diagnostics import add_draw_rank


def test_v2117_draw_rank_and_gap_to_top():
    rows = pd.DataFrame([
        {"home_win_probability": 0.30, "draw_probability": 0.40, "away_win_probability": 0.30},
        {"home_win_probability": 0.42, "draw_probability": 0.39, "away_win_probability": 0.19},
        {"home_win_probability": 0.45, "draw_probability": 0.20, "away_win_probability": 0.35},
    ])
    out = add_draw_rank(rows)
    assert out["draw_rank"].tolist() == [1, 2, 3]
    assert out["draw_gap_to_top"].tolist() == [0.0, 0.03, 0.25]
