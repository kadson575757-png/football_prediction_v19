from pathlib import Path


def test_v2112_exact_scoreline_pattern_script_exists_and_core_importable():
    assert Path("scripts/analyze_v2112_exact_scoreline_pattern_test.py").exists()

    from scripts.analyze_v2112_exact_scoreline_pattern_test import analyze_exact_scoreline_patterns

    assert callable(analyze_exact_scoreline_patterns)

