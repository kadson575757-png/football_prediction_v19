import json

import pandas as pd

from football_prediction_v19.analysis.v2122_rolling_team_bias_shadow_probe import analyze_rolling_team_bias_shadow_probe


def test_v2122_safety_flags_false_and_outputs_exist(tmp_path):
    rows = pd.DataFrame([
        {"match_date": f"2025-03-{day:02d}", "home_team": "Alpha", "away_team": f"T{day}", "actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.45, "draw_probability": 0.30, "away_probability": 0.25, "probability_edge": 0.15}
        for day in range(1, 7)
    ])
    result = analyze_rolling_team_bias_shadow_probe(rows, output_dir=tmp_path)
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
    assert result["post_match_rows_used_count"] == 0
    payload = json.loads((tmp_path / "v2122_summary.json").read_text(encoding="utf-8"))
    assert payload["automatic_betting_enabled"] is False
    assert (tmp_path / "v2122_rolling_team_bias_shadow_rows.csv").exists()
    assert (tmp_path / "v2122_strategy_summary.csv").exists()
    assert (tmp_path / "v2122_asof_audit.csv").exists()
    assert (tmp_path / "v2122_report.md").exists()
