import pandas as pd

from football_prediction_v19.analysis.v2126_external_league_edge_calibration import apply_fixed_high_edge_sharpen


def test_no_adjustment_at_or_below_edge_threshold():
    rows = pd.DataFrame([{"competition": "Bundesliga", "season": "2023/24", "actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.50, "draw_probability": 0.30, "away_probability": 0.20, "probability_edge": edge} for edge in [0.10, 0.15]])
    result = apply_fixed_high_edge_sharpen(rows)
    assert not result["adjustment_applied"].any()
    assert result["shadow_home_win_probability"].tolist() == [0.5, 0.5]
