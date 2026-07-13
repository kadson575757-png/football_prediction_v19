import pandas as pd

from football_prediction_v19.analysis.v2122_rolling_team_bias_shadow_probe import compute_rolling_team_bias_features


def test_history_quality_becomes_ready_after_five_prior_role_matches():
    rows = pd.DataFrame([
        {"match_date": f"2025-01-{day:02d}", "home_team": "Alpha", "away_team": f"T{day}", "actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.45, "draw_probability": 0.30, "away_probability": 0.25}
        for day in range(1, 7)
    ])
    rolling, _ = compute_rolling_team_bias_features(rows)
    assert rolling.iloc[4]["prior_home_matches_count"] == 4
    assert rolling.iloc[4]["home_bias_history_quality"] == "INSUFFICIENT_HISTORY"
    assert rolling.iloc[5]["prior_home_matches_count"] == 5
    assert rolling.iloc[5]["home_bias_history_quality"] == "READY"
