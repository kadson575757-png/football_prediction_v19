from pathlib import Path


def test_v2125_script_exists_and_core_importable():
    assert Path("scripts/analyze_v2125_cross_season_edge_reliability.py").exists()
    from scripts.analyze_v2125_cross_season_edge_reliability import analyze_v2125_cross_season_edge_reliability
    from football_prediction_v19.analysis.v2125_cross_season_edge_reliability import analyze_cross_season_edge_reliability

    assert callable(analyze_v2125_cross_season_edge_reliability)
    assert callable(analyze_cross_season_edge_reliability)
