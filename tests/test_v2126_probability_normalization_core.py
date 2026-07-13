import pandas as pd

from football_prediction_v19.analysis.v2126_external_league_edge_calibration import apply_fixed_high_edge_sharpen


def test_fixed_shadow_probabilities_sum_exactly_one_and_preserve_originals():
    rows = pd.DataFrame([{"competition": "Serie A", "season": "2023/24", "actual_result": "AWAY", "top_probability_outcome": "AWAY", "home_win_probability": 0.20, "draw_probability": 0.25, "away_probability": 0.55, "probability_edge": 0.30}])
    result = apply_fixed_high_edge_sharpen(rows).iloc[0]
    assert result["shadow_home_win_probability"] + result["shadow_draw_probability"] + result["shadow_away_win_probability"] == 1.0
    assert result["original_home_win_probability"] == 0.20
    assert result["original_draw_probability"] == 0.25
    assert result["original_away_win_probability"] == 0.55
