from pathlib import Path


def test_v2104_multi_indicator_shadow_mix_script_exists():
    assert Path("scripts/analyze_v2104_multi_indicator_shadow_mix.py").exists()
    from scripts.analyze_v2104_multi_indicator_shadow_mix import analyze_multi_indicator_shadow_mix

    assert callable(analyze_multi_indicator_shadow_mix)
