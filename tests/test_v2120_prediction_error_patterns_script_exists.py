from pathlib import Path


def test_v2120_prediction_error_patterns_script_exists_and_core_importable():
    assert Path("scripts/analyze_v2120_prediction_error_patterns.py").exists()
    from scripts.analyze_v2120_prediction_error_patterns import analyze_v2120_prediction_error_patterns
    from football_prediction_v19.analysis.v2120_prediction_error_patterns import analyze_prediction_error_patterns

    assert callable(analyze_v2120_prediction_error_patterns)
    assert callable(analyze_prediction_error_patterns)
