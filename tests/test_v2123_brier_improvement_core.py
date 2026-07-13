import pandas as pd

from football_prediction_v19.analysis.v2123_rolling_bias_calibration_robustness import apply_robustness_configuration, brier_loss


def test_brier_loss_and_improvement_are_paired_per_row():
    assert brier_loss(1.0, 0.0, 0.0, "HOME") == 0.0
    rows = pd.DataFrame([{
        "match_date": "2025-03-01", "home_team": "A", "away_team": "B",
        "actual_result": "DRAW", "top_probability_outcome": "AWAY",
        "home_win_probability": 0.30, "draw_probability": 0.30, "away_win_probability": 0.40,
        "prior_away_matches_count": 5, "rolling_away_overprediction_delta": 0.20,
        "away_max_source_date": "2025-02-20", "post_match_rows_used_count": 0,
    }])
    result = apply_robustness_configuration(rows, {"configuration": "C", "strategy_name": "S", "minimum_history": 5, "correction_strength": 0.01}).iloc[0]
    assert result["brier_improvement"] == result["baseline_brier_loss"] - result["shadow_brier_loss"]
    assert result["brier_improvement"] > 0
