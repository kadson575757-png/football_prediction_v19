from pathlib import Path


def test_v2111_analysis_quality_script_exists_and_core_importable():
    assert Path("scripts/evaluate_v2111_pl_2025_26_analysis_quality.py").exists()

    from scripts.evaluate_v2111_pl_2025_26_analysis_quality import evaluate_pl_analysis_quality

    assert callable(evaluate_pl_analysis_quality)

