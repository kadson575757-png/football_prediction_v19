from pathlib import Path


def test_v28_cli_scripts_exist():
    assert Path("scripts/build_v28_supported_eval_sample.py").exists()
    assert Path("scripts/analyze_v28_coverage.py").exists()

