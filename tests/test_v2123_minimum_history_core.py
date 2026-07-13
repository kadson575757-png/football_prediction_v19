import pandas as pd

from football_prediction_v19.analysis.v2123_rolling_bias_calibration_robustness import apply_robustness_configuration


def test_configuration_respects_its_minimum_history():
    rows = pd.DataFrame([{
        "match_date": "2025-03-01", "home_team": "A", "away_team": "B",
        "actual_result": "DRAW", "top_probability_outcome": "AWAY",
        "home_win_probability": 0.30, "draw_probability": 0.30, "away_win_probability": 0.40,
        "prior_away_matches_count": 7, "rolling_away_overprediction_delta": 0.20,
        "away_max_source_date": "2025-02-20", "post_match_rows_used_count": 0,
    }])
    ready = apply_robustness_configuration(rows, {"configuration": "C5", "strategy_name": "S", "minimum_history": 5, "correction_strength": 0.01})
    blocked = apply_robustness_configuration(rows, {"configuration": "C8", "strategy_name": "S", "minimum_history": 8, "correction_strength": 0.01})
    assert bool(ready.iloc[0]["adjustment_applied"])
    assert not bool(blocked.iloc[0]["adjustment_applied"])
