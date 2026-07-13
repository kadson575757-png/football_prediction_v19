import pandas as pd

from football_prediction_v19.analysis.v2126_external_league_edge_calibration import evaluate_external_league_edge_calibration


def test_combined_external_evaluation_can_be_robust(tmp_path):
    competitions = ["League A", "League B"]
    seasons = ["S1", "S2", "S3"]
    inputs = {}
    for competition in competitions:
        for season in seasons:
            inputs[(competition, season)] = pd.DataFrame([{"competition": competition, "season": season, "match_date": "2024-01-02", "as_of_date": "2024-01-01", "actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.55, "draw_probability": 0.27, "away_probability": 0.18, "probability_edge": 0.28}])
    result = evaluate_external_league_edge_calibration(inputs, competitions=competitions, seasons=seasons, expected_fixture_counts={"League A": 1, "League B": 1}, output_dir=tmp_path)
    assert result["competition_seasons_evaluated"] == 6
    assert result["positive_brier_competition_season_count"] == 6
    assert result["external_validation_status"] == "EXTERNAL_EDGE_CALIBRATION_ROBUST"
    assert result["recommendation"] == "EDGE_CALIBRATION_READY_FOR_INTEGRATION_PROBE"
