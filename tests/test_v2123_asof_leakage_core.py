import pandas as pd

from football_prediction_v19.analysis.v2120_prediction_error_patterns import prepare_prediction_rows
from football_prediction_v19.analysis.v2122_rolling_team_bias_shadow_probe import compute_rolling_team_bias_features
from football_prediction_v19.analysis.v2123_rolling_bias_calibration_robustness import apply_robustness_configuration


def test_configuration_rows_keep_strict_asof_sources():
    rows = pd.DataFrame([
        {"match_date": f"2025-02-{day:02d}", "home_team": f"H{day}", "away_team": "Alpha", "actual_result": "DRAW", "top_probability_outcome": "AWAY", "home_win_probability": 0.30, "draw_probability": 0.30, "away_probability": 0.40}
        for day in range(1, 7)
    ])
    rolling, _ = compute_rolling_team_bias_features(prepare_prediction_rows(rows))
    result = apply_robustness_configuration(rolling, {"configuration": "C", "strategy_name": "S", "minimum_history": 5, "correction_strength": 0.01})
    assert result["asof_clean"].all()
    assert result["post_match_rows_used_count"].sum() == 0
    for _, row in result[result["max_source_date"].ne("")].iterrows():
        assert row["max_source_date"] < row["target_match_date"]
