import pandas as pd

from football_prediction_v19.analysis.v2123_rolling_bias_calibration_robustness import compute_team_contribution_summary


def test_team_contribution_sums_and_counts_improvement_direction():
    rows = pd.DataFrame([
        {"configuration": "C", "away_team": "Alpha", "adjustment_applied": True, "baseline_brier_loss": 0.70, "shadow_brier_loss": 0.68, "brier_improvement": 0.02},
        {"configuration": "C", "away_team": "Alpha", "adjustment_applied": True, "baseline_brier_loss": 0.60, "shadow_brier_loss": 0.61, "brier_improvement": -0.01},
    ])
    alpha = compute_team_contribution_summary(rows).iloc[0]
    assert alpha["adjustment_count"] == 2
    assert alpha["total_brier_improvement"] == 0.01
    assert alpha["average_brier_improvement"] == 0.005
    assert alpha["improved_rows_count"] == 1
    assert alpha["worsened_rows_count"] == 1
