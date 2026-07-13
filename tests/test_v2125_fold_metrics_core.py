import pandas as pd

from football_prediction_v19.analysis.v2125_cross_season_edge_reliability import evaluate_holdout_fold, prepare_probe_rows


def test_fold_metrics_count_newly_corrected_rows():
    holdout = prepare_probe_rows(pd.DataFrame([{
        "season": "S3", "actual_result": "DRAW", "top_probability_outcome": "HOME",
        "home_win_probability": 0.34, "draw_probability": 0.335,
        "away_win_probability": 0.325, "probability_edge": 0.005,
    }]))
    metrics, rows = evaluate_holdout_fold(
        holdout, fold_id="F1", selection_seasons=["S1", "S2"], holdout_season="S3",
        selected_configuration="LOW_EDGE_DRAW_LIFT_010",
    )
    assert metrics["newly_corrected_count"] == 1
    assert metrics["newly_broken_count"] == 0
    assert metrics["net_corrected_count"] == 1
    assert metrics["hit_rate_delta"] == 1.0
    assert rows.iloc[0]["season"] == "S3"
