import json

import pandas as pd

from football_prediction_v19.analysis.v2127_edge_calibration_integration import analyze_edge_calibration_integration


def test_v2127_safety_flags_false_and_outputs_exist(tmp_path):
    row = {"actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.55, "draw_probability": 0.27, "away_probability": 0.18, "probability_edge": 0.28}
    result = analyze_edge_calibration_integration(pd.DataFrame([row]), pd.DataFrame([row]), output_dir=tmp_path)
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
    payload = json.loads((tmp_path / "v2127_summary.json").read_text(encoding="utf-8"))
    assert payload["automatic_betting_enabled"] is False
    for filename in ["v2127_integration_rows.csv", "v2127_dataset_summary.csv", "v2127_parity_audit.csv", "v2127_report.md"]:
        assert (tmp_path / filename).exists()
