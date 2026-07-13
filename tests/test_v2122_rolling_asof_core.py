import pandas as pd

from football_prediction_v19.analysis.v2122_rolling_team_bias_shadow_probe import compute_rolling_team_bias_features


def test_rolling_features_use_only_strictly_earlier_dates():
    rows = pd.DataFrame([
        {"match_date": "2025-01-01", "home_team": "Alpha", "away_team": "A", "actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.45, "draw_probability": 0.30, "away_probability": 0.25},
        {"match_date": "2025-01-02", "home_team": "Alpha", "away_team": "B", "actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.45, "draw_probability": 0.30, "away_probability": 0.25},
        {"match_date": "2025-01-03", "home_team": "Alpha", "away_team": "C", "actual_result": "AWAY", "top_probability_outcome": "HOME", "home_win_probability": 0.45, "draw_probability": 0.30, "away_probability": 0.25},
    ])
    rolling, audit = compute_rolling_team_bias_features(rows)
    third = rolling.iloc[2]
    assert third["prior_home_matches_count"] == 2
    assert third["prior_model_home_top_rate"] == 1.0
    assert third["prior_actual_home_win_rate"] == 0.5
    assert third["rolling_home_overprediction_delta"] == 0.5
    assert third["home_max_source_date"] == "2025-01-02"
    assert audit["post_match_rows_used_count"].sum() == 0


def test_same_date_rows_do_not_enter_each_others_history():
    rows = pd.DataFrame([
        {"match_date": "2025-01-01", "home_team": "Alpha", "away_team": "A", "actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.45, "draw_probability": 0.30, "away_probability": 0.25},
        {"match_date": "2025-01-01", "home_team": "Alpha", "away_team": "B", "actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.45, "draw_probability": 0.30, "away_probability": 0.25},
    ])
    rolling, _ = compute_rolling_team_bias_features(rows)
    assert rolling["prior_home_matches_count"].tolist() == [0, 0]
