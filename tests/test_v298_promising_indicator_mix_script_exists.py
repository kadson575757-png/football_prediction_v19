from pathlib import Path

from scripts.analyze_v298_promising_indicator_mix import analyze_promising_indicator_mix


def test_v298_promising_indicator_mix_script_exists():
    assert Path("scripts/analyze_v298_promising_indicator_mix.py").exists()
    assert callable(analyze_promising_indicator_mix)
