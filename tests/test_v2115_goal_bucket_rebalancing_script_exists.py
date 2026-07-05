from pathlib import Path


def test_v2115_goal_bucket_rebalancing_script_exists_and_core_importable():
    assert Path("scripts/analyze_v2115_goal_bucket_rebalancing_test.py").exists()

    from scripts.analyze_v2115_goal_bucket_rebalancing_test import analyze_goal_bucket_rebalancing

    assert callable(analyze_goal_bucket_rebalancing)

