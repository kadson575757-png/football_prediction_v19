import json

import pandas as pd

from football_prediction_v19.analysis.v2125_cross_season_edge_reliability import analyze_cross_season_edge_reliability


def test_v2125_safety_flags_false_and_outputs_exist(tmp_path):
    rows = pd.DataFrame([
        {"season": season, "match_date": f"2025-01-0{index}", "actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.40, "draw_probability": 0.32, "away_win_probability": 0.28, "probability_edge": 0.04}
        for index, season in enumerate(["S1", "S2", "S3"], start=1)
    ])
    result = analyze_cross_season_edge_reliability(rows, output_dir=tmp_path)
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
    payload = json.loads((tmp_path / "v2125_summary.json").read_text(encoding="utf-8"))
    assert payload["automatic_betting_enabled"] is False
    for filename in ["v2125_edge_band_reliability.csv", "v2125_configuration_training_summary.csv", "v2125_holdout_fold_summary.csv", "v2125_holdout_rows.csv", "v2125_report.md"]:
        assert (tmp_path / filename).exists()
