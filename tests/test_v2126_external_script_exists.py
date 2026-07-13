from pathlib import Path


def test_v2126_script_exists_and_core_importable():
    assert Path("scripts/evaluate_v2126_external_league_edge_calibration.py").exists()
    from scripts.evaluate_v2126_external_league_edge_calibration import evaluate_v2126_external_league_edge_calibration
    from football_prediction_v19.analysis.v2126_external_league_edge_calibration import evaluate_external_league_edge_calibration
    assert callable(evaluate_v2126_external_league_edge_calibration)
    assert callable(evaluate_external_league_edge_calibration)
