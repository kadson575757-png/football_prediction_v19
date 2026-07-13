import pandas as pd

from football_prediction_v19.analysis.v2122_rolling_team_bias_shadow_probe import (
    STRATEGIES,
    apply_shadow_strategy,
    compute_strategy_summary,
)


def test_strategy_metrics_count_corrected_and_broken_rows():
    rows = pd.DataFrame([
        {"actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.36, "draw_probability": 0.35, "away_win_probability": 0.29, "rolling_home_overprediction_delta": 0.20, "home_bias_history_quality": "READY", "rolling_away_overprediction_delta": 0.0, "away_bias_history_quality": "READY"},
        {"actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.36, "draw_probability": 0.35, "away_win_probability": 0.29, "rolling_home_overprediction_delta": 0.20, "home_bias_history_quality": "READY", "rolling_away_overprediction_delta": 0.0, "away_bias_history_quality": "READY"},
    ])
    expanded = pd.concat([apply_shadow_strategy(rows, strategy) for strategy in STRATEGIES], ignore_index=True)
    summary = compute_strategy_summary(expanded).set_index("strategy_name")
    probe = summary.loc["HOME_BIAS_002"]
    assert probe["adjustment_applied_count"] == 2
    assert probe["newly_corrected_count"] == 1
    assert probe["newly_broken_count"] == 1
    assert probe["net_corrected_count"] == 0
    assert probe["draw_prediction_count"] == 2
