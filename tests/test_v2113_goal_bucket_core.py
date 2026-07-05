from scripts.analyze_v2113_exact_scoreline_pattern_goal_bucket_test import goal_bucket


def test_v2113_goal_bucket_boundaries():
    assert goal_bucket(0) == "GOALS_0_1"
    assert goal_bucket(1) == "GOALS_0_1"
    assert goal_bucket(2) == "GOALS_2_3"
    assert goal_bucket(3) == "GOALS_2_3"
    assert goal_bucket(4) == "GOALS_4_PLUS"
    assert goal_bucket(5) == "GOALS_4_PLUS"

