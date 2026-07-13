import pandas as pd

from football_prediction_v19.analysis.v2125_cross_season_edge_reliability import apply_shadow_configuration, prepare_probe_rows
from football_prediction_v19.analysis.v2126_external_league_edge_calibration import apply_fixed_high_edge_sharpen


def test_fixed_high_edge_sharpen_matches_v2125_exactly():
    raw = pd.DataFrame([{"competition": "La Liga", "season": "2023/24", "actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.55, "draw_probability": 0.27, "away_probability": 0.18, "probability_edge": 0.28}])
    external = apply_fixed_high_edge_sharpen(raw).iloc[0]
    reference = apply_shadow_configuration(prepare_probe_rows(raw), "HIGH_EDGE_SHARPEN_005").iloc[0]
    for column in ["shadow_home_win_probability", "shadow_draw_probability", "shadow_away_win_probability", "shadow_top_outcome"]:
        assert external[column] == reference[column]
