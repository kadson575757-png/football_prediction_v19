from pathlib import Path


def test_v2105_further_indicator_shadow_mix_script_exists():
    assert Path("scripts/analyze_v2105_further_indicator_shadow_mix.py").exists()
    from scripts.analyze_v2105_further_indicator_shadow_mix import analyze_further_indicator_shadow_mix

    assert callable(analyze_further_indicator_shadow_mix)
