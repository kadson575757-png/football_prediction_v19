import pandas as pd

from football_prediction_v19.analysis.v2120_prediction_error_patterns import prepare_prediction_rows
from football_prediction_v19.analysis.v2121_team_specific_bias_drilldown import add_wrong_high_confidence, compute_team_involved_error_summary


def test_team_involved_error_metrics():
    rows = add_wrong_high_confidence(prepare_prediction_rows(pd.DataFrame([
        {"home_team": "Alpha", "away_team": "B", "actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.48, "draw_probability": 0.29, "away_probability": 0.23, "probability_edge": 0.19},
        {"home_team": "C", "away_team": "Alpha", "actual_result": "DRAW", "top_probability_outcome": "AWAY", "home_win_probability": 0.25, "draw_probability": 0.29, "away_probability": 0.46, "probability_edge": 0.17},
        {"home_team": "Alpha", "away_team": "D", "actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.51, "draw_probability": 0.27, "away_probability": 0.22, "probability_edge": 0.24},
    ])))
    alpha = compute_team_involved_error_summary(rows).set_index("team").loc["Alpha"]
    assert alpha["involved_matches_count"] == 3
    assert alpha["involved_hit_count"] == 1
    assert alpha["involved_miss_count"] == 2
    assert alpha["involved_hit_rate"] == 0.3333
    assert alpha["most_common_error_type_count"] == 1
    assert alpha["home_top_actual_draw_involved_count"] == 1
    assert alpha["away_top_actual_draw_involved_count"] == 1
    assert alpha["wrong_high_confidence_involved_count"] == 2
