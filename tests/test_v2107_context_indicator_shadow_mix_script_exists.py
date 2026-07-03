import pandas as pd

from scripts.analyze_v2107_context_indicator_shadow_mix import analyze_context_indicator_shadow_mix


def test_v2107_context_indicator_shadow_mix_script_writes_outputs(tmp_path):
    rows = tmp_path / "rows.csv"
    pd.DataFrame([{
        "home_win_probability": 0.42,
        "draw_probability": 0.30,
        "away_win_probability": 0.28,
        "real_result": "HOME_WIN",
        "rsp_adjusted_home_win_probability": 0.45,
        "rsp_adjusted_draw_probability": 0.29,
        "rsp_adjusted_away_probability": 0.26,
        "rsp_adjustment_applied": True,
        "v2107_mix_adjusted_home_win_probability": 0.44,
        "v2107_mix_adjusted_draw_probability": 0.30,
        "v2107_mix_adjusted_away_probability": 0.26,
        "v2107_combined_mix_adjusted_home_win_probability": 0.45,
        "v2107_combined_mix_adjusted_draw_probability": 0.29,
        "v2107_combined_mix_adjusted_away_probability": 0.26,
    }]).to_csv(rows, index=False)

    result = analyze_context_indicator_shadow_mix(rows, tmp_path / "out")

    assert result["v2107_context_indicator_shadow_mix_status"] == "READY"
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
    assert (tmp_path / "out" / "v2107_context_indicator_shadow_mix_rows.csv").exists()
    assert (tmp_path / "out" / "v2107_context_indicator_shadow_mix_report.md").exists()
