import pandas as pd

from football_prediction_v19.analysis.v2120_prediction_error_patterns import (
    compute_team_error_summary,
    prepare_prediction_rows,
)


def test_team_home_away_rates_and_overprediction_delta():
    rows = prepare_prediction_rows(pd.DataFrame([
        {"home_team": "Alpha", "away_team": "Beta", "actual_result": "DRAW", "top_probability_outcome": "HOME"},
        {"home_team": "Alpha", "away_team": "Gamma", "actual_result": "HOME", "top_probability_outcome": "HOME"},
        {"home_team": "Delta", "away_team": "Alpha", "actual_result": "HOME", "top_probability_outcome": "AWAY"},
        {"home_team": "Echo", "away_team": "Alpha", "actual_result": "AWAY", "top_probability_outcome": "AWAY"},
    ]))
    summary = compute_team_error_summary(rows[rows["evaluable"]])
    alpha = summary.set_index("team").loc["Alpha"]
    assert alpha["home_matches_count"] == 2
    assert alpha["home_prediction_top_count"] == 2
    assert alpha["home_prediction_hit_rate"] == 0.5
    assert alpha["actual_home_win_rate"] == 0.5
    assert alpha["model_home_top_rate"] == 1.0
    assert alpha["home_overprediction_delta"] == 0.5
    assert alpha["away_matches_count"] == 2
    assert alpha["away_prediction_top_count"] == 2
    assert alpha["away_prediction_hit_rate"] == 0.5
    assert alpha["actual_away_win_rate"] == 0.5
    assert alpha["away_overprediction_delta"] == 0.5
    assert alpha["team_involved_miss_count"] == 2
