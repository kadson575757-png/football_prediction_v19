from pathlib import Path


def test_v2114_goal_bucket_bias_script_exists_and_core_importable():
    assert Path("scripts/analyze_v2114_goal_bucket_bias_diagnostics.py").exists()

    from scripts.analyze_v2114_goal_bucket_bias_diagnostics import analyze_goal_bucket_bias

    assert callable(analyze_goal_bucket_bias)

