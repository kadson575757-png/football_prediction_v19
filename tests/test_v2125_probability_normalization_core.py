import pandas as pd

from football_prediction_v19.analysis.v2125_cross_season_edge_reliability import apply_shadow_configuration, prepare_probe_rows


def test_every_shadow_probability_vector_is_valid_and_sums_exactly_one():
    rows = prepare_probe_rows(pd.DataFrame([{
        "season": "S1", "actual_result": "DRAW", "top_probability_outcome": "HOME",
        "home_win_probability": 0.36, "draw_probability": 0.34,
        "away_win_probability": 0.30, "probability_edge": 0.02,
    }]))
    for configuration in ["LOW_EDGE_UNIFORM_SHRINK_015", "LOW_EDGE_DRAW_LIFT_010", "MEDIUM_EDGE_UNIFORM_SHRINK_005"]:
        result = apply_shadow_configuration(rows, configuration).iloc[0]
        values = [result["shadow_home_win_probability"], result["shadow_draw_probability"], result["shadow_away_win_probability"]]
        assert all(0 <= value <= 1 for value in values)
        assert sum(values) == 1.0
