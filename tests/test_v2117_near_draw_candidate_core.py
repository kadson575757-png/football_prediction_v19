import pandas as pd

from football_prediction_v19.analysis.v2117_draw_bias_diagnostics import add_draw_rank, add_near_draw_candidates


def test_v2117_near_draw_candidate_thresholds():
    rows = pd.DataFrame([
        {"home_win_probability": 0.33, "draw_probability": 0.30, "away_win_probability": 0.37},
        {"home_win_probability": 0.40, "draw_probability": 0.27, "away_win_probability": 0.33},
        {"home_win_probability": 0.40, "draw_probability": 0.29, "away_win_probability": 0.31},
    ])
    out = add_near_draw_candidates(add_draw_rank(rows), min_draw_probability=0.28, near_draw_edge=0.05)
    assert out["near_draw_candidate"].tolist() == [False, False, False]
    rows.loc[0, "away_win_probability"] = 0.34
    out = add_near_draw_candidates(add_draw_rank(rows), min_draw_probability=0.28, near_draw_edge=0.05)
    assert out["near_draw_candidate"].tolist()[0] is True
