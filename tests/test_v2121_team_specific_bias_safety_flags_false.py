import json

import pandas as pd

from football_prediction_v19.analysis.v2121_team_specific_bias_drilldown import analyze_team_specific_bias_drilldown


def test_v2121_safety_flags_false_and_artifacts_exist(tmp_path):
    rows = pd.DataFrame([
        {"home_team": "Bournemouth", "away_team": "B", "actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.48, "draw_probability": 0.29, "away_probability": 0.23, "probability_edge": 0.19},
        {"home_team": "C", "away_team": "Liverpool", "actual_result": "DRAW", "top_probability_outcome": "AWAY", "home_win_probability": 0.25, "draw_probability": 0.29, "away_probability": 0.46, "probability_edge": 0.17},
    ])
    result = analyze_team_specific_bias_drilldown(rows, output_dir=tmp_path)
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
    assert result["bournemouth_home_matches_count"] == 1
    assert result["liverpool_away_matches_count"] == 1
    payload = json.loads((tmp_path / "v2121_team_specific_bias_drilldown_summary.json").read_text(encoding="utf-8"))
    assert payload["automatic_betting_enabled"] is False
    assert (tmp_path / "v2121_home_team_bias_summary.csv").exists()
    assert (tmp_path / "v2121_team_bias_severity_summary.csv").exists()
    assert (tmp_path / "v2121_bournemouth_home_drilldown.csv").exists()
    assert (tmp_path / "v2121_liverpool_away_drilldown.csv").exists()
