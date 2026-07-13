from pathlib import Path


def test_v2122_script_exists_and_core_is_importable():
    assert Path("scripts/analyze_v2122_rolling_team_bias_shadow_probe.py").exists()
    from scripts.analyze_v2122_rolling_team_bias_shadow_probe import analyze_v2122_rolling_team_bias_shadow_probe
    from football_prediction_v19.analysis.v2122_rolling_team_bias_shadow_probe import analyze_rolling_team_bias_shadow_probe

    assert callable(analyze_v2122_rolling_team_bias_shadow_probe)
    assert callable(analyze_rolling_team_bias_shadow_probe)
