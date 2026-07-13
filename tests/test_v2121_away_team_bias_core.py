import pandas as pd

from football_prediction_v19.analysis.v2120_prediction_error_patterns import prepare_prediction_rows
from football_prediction_v19.analysis.v2121_team_specific_bias_drilldown import add_wrong_high_confidence, compute_away_team_bias_summary


def test_away_team_bias_metrics():
    rows = add_wrong_high_confidence(prepare_prediction_rows(pd.DataFrame([
        {"home_team": "A", "away_team": "Omega", "actual_result": "AWAY", "top_probability_outcome": "AWAY", "home_win_probability": 0.25, "draw_probability": 0.25, "away_probability": 0.50, "probability_edge": 0.25},
        {"home_team": "B", "away_team": "Omega", "actual_result": "DRAW", "top_probability_outcome": "AWAY", "home_win_probability": 0.22, "draw_probability": 0.30, "away_probability": 0.48, "probability_edge": 0.18},
        {"home_team": "C", "away_team": "Omega", "actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.42, "draw_probability": 0.29, "away_probability": 0.29, "probability_edge": 0.13},
    ])))
    omega = compute_away_team_bias_summary(rows).set_index("team").loc["Omega"]
    assert omega["away_matches_count"] == 3
    assert omega["model_away_top_count"] == 2
    assert omega["actual_away_win_count"] == 1
    assert omega["actual_away_draw_count"] == 1
    assert omega["actual_away_loss_count"] == 1
    assert omega["away_overprediction_delta"] == 0.3334
    assert omega["away_top_hit_count"] == 1
    assert omega["away_top_miss_count"] == 1
    assert omega["away_top_actual_draw_count"] == 1
    assert omega["wrong_high_confidence_away_count"] == 1
