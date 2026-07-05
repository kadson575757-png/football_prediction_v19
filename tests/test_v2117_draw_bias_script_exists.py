from pathlib import Path


def test_v2117_draw_bias_script_exists_and_core_importable():
    assert Path("scripts/analyze_v2117_draw_bias_diagnostics.py").exists()
    from scripts.analyze_v2117_draw_bias_diagnostics import analyze_v2117_draw_bias_diagnostics
    from football_prediction_v19.analysis.v2117_draw_bias_diagnostics import analyze_draw_bias

    assert callable(analyze_v2117_draw_bias_diagnostics)
    assert callable(analyze_draw_bias)
