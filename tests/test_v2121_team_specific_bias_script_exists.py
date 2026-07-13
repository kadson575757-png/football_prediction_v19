from pathlib import Path


def test_v2121_script_exists_and_core_is_importable():
    assert Path("scripts/analyze_v2121_team_specific_bias_drilldown.py").exists()
    from scripts.analyze_v2121_team_specific_bias_drilldown import analyze_v2121_team_specific_bias_drilldown
    from football_prediction_v19.analysis.v2121_team_specific_bias_drilldown import analyze_team_specific_bias_drilldown

    assert callable(analyze_v2121_team_specific_bias_drilldown)
    assert callable(analyze_team_specific_bias_drilldown)
