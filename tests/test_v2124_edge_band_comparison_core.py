import pandas as pd

from football_prediction_v19.analysis.v2124_pl_multi_season_robustness import (
    compute_edge_band_by_season,
    prepare_season_rows,
    v2124_edge_band,
)


def test_edge_bands_and_season_rates_are_correct():
    assert v2124_edge_band(0.03) == "EDGE_0_03"
    assert v2124_edge_band(0.04) == "EDGE_3_05"
    assert v2124_edge_band(0.07) == "EDGE_5_08"
    assert v2124_edge_band(0.09) == "EDGE_8_10"
    assert v2124_edge_band(0.12) == "EDGE_10_15"
    assert v2124_edge_band(0.16) == "EDGE_GT_15"
    rows = prepare_season_rows(pd.DataFrame([
        {"actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.36, "draw_probability": 0.34, "away_probability": 0.30, "probability_edge": 0.02},
        {"actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.36, "draw_probability": 0.34, "away_probability": 0.30, "probability_edge": 0.02},
    ]), "2023/24")
    band = compute_edge_band_by_season(rows, ["2023/24"]).set_index("edge_band").loc["EDGE_0_03"]
    assert band["count"] == 2
    assert band["hit_rate"] == 0.5
    assert band["actual_draw_rate"] == 0.5
