import json

import pandas as pd

from football_prediction_v19.analysis.v2124_pl_multi_season_robustness import evaluate_pl_multi_season_robustness


def test_v2124_safety_flags_false_and_outputs_exist(tmp_path):
    rows = pd.DataFrame([{
        "match_date": "2024-01-02", "as_of_date": "2024-01-01", "actual_result": "HOME",
        "top_probability_outcome": "HOME", "home_win_probability": 0.5,
        "draw_probability": 0.3, "away_probability": 0.2,
    }])
    result = evaluate_pl_multi_season_robustness({"2023/24": rows}, seasons=["2023/24"], expected_fixture_count=1, output_dir=tmp_path)
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
    payload = json.loads((tmp_path / "v2124_summary.json").read_text(encoding="utf-8"))
    assert payload["automatic_betting_enabled"] is False
    for filename in ["v2124_season_summary.csv", "v2124_combined_rows.csv", "v2124_error_type_by_season.csv", "v2124_edge_band_by_season.csv", "v2124_asof_audit.csv", "v2124_report.md"]:
        assert (tmp_path / filename).exists()
