from pathlib import Path


def test_v2119_draw_signal_shadow_script_exists_and_core_importable():
    assert Path("scripts/analyze_v2119_draw_signal_shadow_probe.py").exists()
    from scripts.analyze_v2119_draw_signal_shadow_probe import analyze_v2119_draw_signal_shadow_probe
    from football_prediction_v19.analysis.v2119_draw_signal_shadow_probe import analyze_draw_signal_shadow_probe

    assert callable(analyze_v2119_draw_signal_shadow_probe)
    assert callable(analyze_draw_signal_shadow_probe)
