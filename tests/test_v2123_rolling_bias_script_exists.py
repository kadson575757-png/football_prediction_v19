from pathlib import Path


def test_v2123_script_exists_and_core_importable():
    assert Path("scripts/analyze_v2123_rolling_bias_calibration_robustness.py").exists()
    from scripts.analyze_v2123_rolling_bias_calibration_robustness import analyze_v2123_rolling_bias_calibration_robustness
    from football_prediction_v19.analysis.v2123_rolling_bias_calibration_robustness import analyze_rolling_bias_calibration_robustness

    assert callable(analyze_v2123_rolling_bias_calibration_robustness)
    assert callable(analyze_rolling_bias_calibration_robustness)
