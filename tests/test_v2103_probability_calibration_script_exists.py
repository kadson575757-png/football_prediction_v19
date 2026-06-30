from pathlib import Path

from scripts import analyze_v2103_probability_calibration


def test_v2103_probability_calibration_script_exists_and_core_importable():
    assert Path("scripts/analyze_v2103_probability_calibration.py").exists()
    assert callable(analyze_v2103_probability_calibration.analyze_probability_calibration)
