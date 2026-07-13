import pandas as pd

from football_prediction_v19.analysis.v2120_prediction_error_patterns import prepare_prediction_rows
from football_prediction_v19.analysis.v2121_team_specific_bias_drilldown import (
    add_wrong_high_confidence,
    compute_home_team_bias_summary,
)


def test_home_team_bias_metrics():
    rows = add_wrong_high_confidence(prepare_prediction_rows(pd.DataFrame([
        {"home_team": "Alpha", "away_team": "B", "actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.52, "draw_probability": 0.28, "away_probability": 0.20, "probability_edge": 0.24},
        {"home_team": "Alpha", "away_team": "C", "actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.48, "draw_probability": 0.30, "away_probability": 0.22, "probability_edge": 0.18},
        {"home_team": "Alpha", "away_team": "D", "actual_result": "AWAY", "top_probability_outcome": "AWAY", "home_win_probability": 0.31, "draw_probability": 0.29, "away_probability": 0.40, "probability_edge": 0.09},
    ])))
    alpha = compute_home_team_bias_summary(rows).set_index("team").loc["Alpha"]
    assert alpha["home_matches_count"] == 3
    assert alpha["model_home_top_count"] == 2
    assert alpha["actual_home_win_count"] == 1
    assert alpha["actual_home_draw_count"] == 1
    assert alpha["actual_home_loss_count"] == 1
    assert alpha["model_home_top_rate"] == 0.6667
    assert alpha["actual_home_win_rate"] == 0.3333
    assert alpha["home_overprediction_delta"] == 0.3334
    assert alpha["home_top_hit_count"] == 1
    assert alpha["home_top_miss_count"] == 1
    assert alpha["home_top_hit_rate"] == 0.5
    assert alpha["home_top_actual_draw_count"] == 1
    assert alpha["wrong_high_confidence_home_count"] == 1
