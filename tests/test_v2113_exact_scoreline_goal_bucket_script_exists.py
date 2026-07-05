from pathlib import Path


def test_v2113_exact_scoreline_goal_bucket_script_exists_and_core_importable():
    assert Path("scripts/analyze_v2113_exact_scoreline_pattern_goal_bucket_test.py").exists()

    from scripts.analyze_v2113_exact_scoreline_pattern_goal_bucket_test import analyze_exact_scoreline_goal_buckets

    assert callable(analyze_exact_scoreline_goal_buckets)

