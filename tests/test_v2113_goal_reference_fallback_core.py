import pandas as pd

from scripts.analyze_v2113_exact_scoreline_pattern_goal_bucket_test import choose_final_goal_reference, goal_reference_stats


def _stats(goals):
    return goal_reference_stats(pd.DataFrame([{"actual_home_goals": value, "actual_away_goals": 0} for value in goals]))


def test_v2113_goal_reference_fallback_priority():
    refs = {"exact_pair": _stats([1]), "combined_single": _stats([2]), "home_single": _stats([4]), "away_single": _stats([5])}
    assert choose_final_goal_reference(refs)["source"] == "EXACT_PAIR"

    refs["exact_pair"] = _stats([])
    assert choose_final_goal_reference(refs)["source"] == "COMBINED_SINGLE"

    refs["combined_single"] = _stats([])
    assert choose_final_goal_reference(refs)["source"] == "HOME_SINGLE"

    refs["home_single"] = _stats([])
    assert choose_final_goal_reference(refs)["source"] == "AWAY_SINGLE"

    refs["away_single"] = _stats([])
    assert choose_final_goal_reference(refs)["source"] == "NO_REFERENCE"

