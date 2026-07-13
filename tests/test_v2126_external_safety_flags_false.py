import json

import pandas as pd

from football_prediction_v19.analysis.v2126_external_league_edge_calibration import evaluate_external_league_edge_calibration


def test_v2126_safety_flags_false_and_outputs_exist(tmp_path):
    rows = pd.DataFrame([{"competition": "La Liga", "season": "S1", "match_date": "2024-01-02", "as_of_date": "2024-01-01", "actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.55, "draw_probability": 0.27, "away_probability": 0.18, "probability_edge": 0.28}])
    result = evaluate_external_league_edge_calibration({("La Liga", "S1"): rows}, competitions=["La Liga"], seasons=["S1"], expected_fixture_counts={"La Liga": 1}, output_dir=tmp_path)
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
    payload = json.loads((tmp_path / "v2126_summary.json").read_text(encoding="utf-8"))
    assert payload["automatic_betting_enabled"] is False
    for filename in ["v2126_competition_season_summary.csv", "v2126_competition_summary.csv", "v2126_external_rows.csv", "v2126_asof_audit.csv", "v2126_report.md"]:
        assert (tmp_path / filename).exists()
