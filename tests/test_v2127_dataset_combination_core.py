import pandas as pd

from football_prediction_v19.analysis.v2127_edge_calibration_integration import analyze_edge_calibration_integration


def test_premier_and_external_datasets_are_combined_without_loss(tmp_path):
    premier = pd.DataFrame([{"actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.55, "draw_probability": 0.27, "away_probability": 0.18, "probability_edge": 0.28}])
    external = pd.DataFrame([{"actual_result": "AWAY", "top_probability_outcome": "AWAY", "home_win_probability": 0.18, "draw_probability": 0.27, "away_probability": 0.55, "probability_edge": 0.28}, {"actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.40, "draw_probability": 0.35, "away_probability": 0.25, "probability_edge": 0.05}])
    result = analyze_edge_calibration_integration(premier, external, output_dir=tmp_path)
    summary = pd.read_csv(tmp_path / "v2127_dataset_summary.csv")
    assert result["rows_loaded"] == 3
    assert set(summary["dataset_source"]) == {"PREMIER_LEAGUE_MULTI_SEASON", "EXTERNAL_LEAGUES", "COMBINED"}
    assert summary.set_index("dataset_source").loc["EXTERNAL_LEAGUES", "rows_loaded"] == 2
