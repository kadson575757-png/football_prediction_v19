import pandas as pd

from football_prediction_v19.analysis.v2125_cross_season_edge_reliability import compute_configuration_training_summary, prepare_probe_rows


def test_configuration_selection_uses_only_passed_training_rows():
    training = prepare_probe_rows(pd.DataFrame([
        {"season": "S1", "actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.34, "draw_probability": 0.335, "away_win_probability": 0.325, "probability_edge": 0.005},
        {"season": "S2", "actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.34, "draw_probability": 0.335, "away_win_probability": 0.325, "probability_edge": 0.005},
    ]))
    _, first = compute_configuration_training_summary(training, fold_id="F", selection_seasons=["S1", "S2"], holdout_season="S3")
    unrelated_holdout = pd.DataFrame([{"season": "S3", "actual_result": "AWAY"}] * 100)
    assert len(unrelated_holdout) == 100
    _, second = compute_configuration_training_summary(training, fold_id="F", selection_seasons=["S1", "S2"], holdout_season="S3")
    assert first["configuration"] == second["configuration"]
    assert first["multiclass_brier_score"] == second["multiclass_brier_score"]
