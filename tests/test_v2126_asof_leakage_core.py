import pandas as pd

from football_prediction_v19.analysis.v2126_external_league_edge_calibration import evaluate_external_league_edge_calibration


def test_asof_audit_flags_source_on_target_date(tmp_path):
    rows = pd.DataFrame([
        {"competition": "Serie A", "season": "S1", "match_date": "2024-01-02", "as_of_date": "2024-01-01", "actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.5, "draw_probability": 0.3, "away_probability": 0.2, "probability_edge": 0.2},
        {"competition": "Serie A", "season": "S1", "match_date": "2024-01-03", "as_of_date": "2024-01-03", "actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.4, "draw_probability": 0.35, "away_probability": 0.25, "probability_edge": 0.05},
    ])
    evaluate_external_league_edge_calibration({("Serie A", "S1"): rows}, competitions=["Serie A"], seasons=["S1"], expected_fixture_counts={"Serie A": 2}, output_dir=tmp_path)
    audit = pd.read_csv(tmp_path / "v2126_asof_audit.csv")
    assert audit["asof_clean"].tolist() == [True, False]
