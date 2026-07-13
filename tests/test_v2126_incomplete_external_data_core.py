import pandas as pd

from football_prediction_v19.analysis.v2126_external_league_edge_calibration import evaluate_external_league_edge_calibration


def test_incomplete_competition_seasons_are_reported(tmp_path):
    rows = pd.DataFrame([{"competition": "La Liga", "season": "S1", "actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.5, "draw_probability": 0.3, "away_probability": 0.2, "probability_edge": 0.2}])
    result = evaluate_external_league_edge_calibration({("La Liga", "S1"): rows}, competitions=["La Liga", "Bundesliga"], seasons=["S1", "S2", "S3"], load_info={("Bundesliga", "S1"): {"load_status": "FAILED", "load_reason": "stub failure", "fixtures_found": 0}}, expected_fixture_counts={"La Liga": 1, "Bundesliga": 1}, output_dir=tmp_path)
    summary = pd.read_csv(tmp_path / "v2126_competition_season_summary.csv", keep_default_na=False)
    assert len(summary) == 6
    assert result["external_validation_status"] == "EXTERNAL_DATA_INSUFFICIENT"
    failed = summary[(summary["competition"] == "Bundesliga") & (summary["season"] == "S1")].iloc[0]
    assert failed["load_status"] == "FAILED"
    assert failed["load_reason"] == "stub failure"
