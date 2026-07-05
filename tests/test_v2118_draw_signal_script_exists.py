from pathlib import Path


def test_v2118_draw_signal_script_exists_and_core_importable():
    assert Path("scripts/analyze_v2118_draw_signal_discovery.py").exists()
    from scripts.analyze_v2118_draw_signal_discovery import analyze_v2118_draw_signal_discovery
    from football_prediction_v19.analysis.v2118_draw_signal_discovery import analyze_draw_signal_discovery

    assert callable(analyze_v2118_draw_signal_discovery)
    assert callable(analyze_draw_signal_discovery)
