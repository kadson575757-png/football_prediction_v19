from pathlib import Path


def test_v2127_script_exists_and_core_importable():
    assert Path("scripts/run_v2127_edge_calibration_integration_probe.py").exists()
    from scripts.run_v2127_edge_calibration_integration_probe import run_v2127_edge_calibration_integration_probe
    from football_prediction_v19.analysis.v2127_edge_calibration_integration import analyze_edge_calibration_integration
    assert callable(run_v2127_edge_calibration_integration_probe)
    assert callable(analyze_edge_calibration_integration)
