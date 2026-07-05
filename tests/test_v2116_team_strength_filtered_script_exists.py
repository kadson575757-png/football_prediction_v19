from pathlib import Path


def test_v2116_team_strength_filtered_script_exists_and_core_importable():
    assert Path("scripts/analyze_v2116_team_strength_filtered_pattern_test.py").exists()
    from scripts.analyze_v2116_team_strength_filtered_pattern_test import analyze_v2116_team_strength_filtered_pattern_test
    from football_prediction_v19.analysis.v2116_team_strength_filtered_pattern_test import analyze_team_strength_filtered_patterns

    assert callable(analyze_v2116_team_strength_filtered_pattern_test)
    assert callable(analyze_team_strength_filtered_patterns)
