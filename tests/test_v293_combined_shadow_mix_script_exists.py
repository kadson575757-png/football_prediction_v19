from pathlib import Path

from scripts.analyze_v293_combined_shadow_mix import analyze_combined_shadow_mix


def test_v293_combined_shadow_mix_script_exists():
    assert Path("scripts/analyze_v293_combined_shadow_mix.py").exists()
    assert callable(analyze_combined_shadow_mix)
