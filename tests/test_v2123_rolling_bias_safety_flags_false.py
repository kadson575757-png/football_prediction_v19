import json

import pandas as pd

from football_prediction_v19.analysis.v2123_rolling_bias_calibration_robustness import analyze_rolling_bias_calibration_robustness


def test_v2123_safety_flags_false_and_outputs_exist(tmp_path):
    rows = pd.DataFrame([
        {"match_date": f"2025-04-{day:02d}", "home_team": f"H{day}", "away_team": "Alpha", "actual_result": "DRAW", "top_probability_outcome": "AWAY", "home_win_probability": 0.30, "draw_probability": 0.30, "away_probability": 0.40}
        for day in range(1, 12)
    ])
    result = analyze_rolling_bias_calibration_robustness(rows, output_dir=tmp_path)
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
    assert result["post_match_rows_used_count"] == 0
    payload = json.loads((tmp_path / "v2123_summary.json").read_text(encoding="utf-8"))
    assert payload["automatic_betting_enabled"] is False
    assert (tmp_path / "v2123_configuration_summary.csv").exists()
    assert (tmp_path / "v2123_period_robustness_summary.csv").exists()
    assert (tmp_path / "v2123_team_contribution_summary.csv").exists()
    assert (tmp_path / "v2123_bootstrap_summary.csv").exists()
    assert (tmp_path / "v2123_asof_audit.csv").exists()
    assert (tmp_path / "v2123_report.md").exists()
