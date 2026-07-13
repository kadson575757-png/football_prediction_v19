import pandas as pd

from football_prediction_v19.analysis.v2126_external_league_edge_calibration import compute_competition_season_metrics


def test_competition_season_metrics_count_shadow_changes():
    rows = pd.DataFrame([{"competition": "La Liga", "season": "2023/24", "match_date": "2024-01-02", "as_of_date": "2024-01-01", "actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.55, "draw_probability": 0.27, "away_probability": 0.18, "probability_edge": 0.28}])
    metrics, applied = compute_competition_season_metrics(rows, competition="La Liga", season="2023/24", expected_fixture_count=1)
    assert metrics["competition_season_status"] == "READY"
    assert metrics["evaluable_count"] == 1
    assert metrics["adjustment_applied_count"] == 1
    assert metrics["baseline_hit_rate"] == metrics["shadow_hit_rate"] == 1.0
    assert metrics["brier_improvement"] > 0
    assert applied.iloc[0]["fixed_configuration"] == "HIGH_EDGE_SHARPEN_005"
