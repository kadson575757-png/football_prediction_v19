import pandas as pd

from scripts.analyze_v2112_exact_scoreline_pattern_test import actual_result, compute_summary


def test_v2112_pattern_hit_rate_excludes_no_reference_and_no_clear_top(tmp_path):
    rows = pd.DataFrame([
        {
            "actual_result": "HOME",
            "final_reference_top_outcome": "HOME",
            "final_reference_source": "EXACT_PAIR",
            "reference_hit": True,
            "home_own_pattern_seen_before": True,
            "away_own_pattern_seen_before": False,
            "exact_pair_reference_count": 1,
            "exact_pair_top_outcome": "HOME",
            "combined_single_reference_count": 1,
            "combined_single_top_outcome": "AWAY",
            "home_single_reference_count": 1,
            "home_single_top_outcome": "HOME",
            "away_single_reference_count": 0,
            "away_single_top_outcome": "NO_REFERENCE",
        },
        {
            "actual_result": "HOME",
            "final_reference_top_outcome": "AWAY",
            "final_reference_source": "COMBINED_SINGLE",
            "reference_hit": False,
            "home_own_pattern_seen_before": False,
            "away_own_pattern_seen_before": True,
            "exact_pair_reference_count": 0,
            "exact_pair_top_outcome": "NO_REFERENCE",
            "combined_single_reference_count": 1,
            "combined_single_top_outcome": "HOME",
            "home_single_reference_count": 1,
            "home_single_top_outcome": "DRAW",
            "away_single_reference_count": 1,
            "away_single_top_outcome": "HOME",
        },
        {
            "actual_result": "DRAW",
            "final_reference_top_outcome": "NO_REFERENCE",
            "final_reference_source": "NO_REFERENCE",
            "reference_hit": "",
            "home_own_pattern_seen_before": False,
            "away_own_pattern_seen_before": False,
            "exact_pair_reference_count": 0,
            "exact_pair_top_outcome": "NO_REFERENCE",
            "combined_single_reference_count": 0,
            "combined_single_top_outcome": "NO_REFERENCE",
            "home_single_reference_count": 0,
            "home_single_top_outcome": "NO_REFERENCE",
            "away_single_reference_count": 0,
            "away_single_top_outcome": "NO_REFERENCE",
        },
        {
            "actual_result": "AWAY",
            "final_reference_top_outcome": "NO_CLEAR_TOP",
            "final_reference_source": "HOME_SINGLE",
            "reference_hit": "",
            "home_own_pattern_seen_before": False,
            "away_own_pattern_seen_before": False,
            "exact_pair_reference_count": 1,
            "exact_pair_top_outcome": "NO_CLEAR_TOP",
            "combined_single_reference_count": 1,
            "combined_single_top_outcome": "NO_CLEAR_TOP",
            "home_single_reference_count": 1,
            "home_single_top_outcome": "NO_CLEAR_TOP",
            "away_single_reference_count": 1,
            "away_single_top_outcome": "NO_CLEAR_TOP",
        },
    ])

    assert actual_result(2, 1) == "HOME"
    assert actual_result(1, 1) == "DRAW"
    assert actual_result(0, 1) == "AWAY"
    summary = compute_summary(rows, fixtures_loaded=4, competition="Premier League", season="2025/26", output_dir=tmp_path)

    assert summary["final_reference_evaluable_count"] == 2
    assert summary["final_reference_hit_count"] == 1
    assert summary["final_reference_miss_count"] == 1
    assert summary["final_reference_hit_rate"] == 0.5
    assert summary["evaluatable_reference_count"] == 2
    assert summary["reference_hit_count"] == 1
    assert summary["reference_miss_count"] == 1
    assert summary["reference_hit_rate"] == 0.5
    assert summary["no_reference_count"] == 1
    assert summary["no_clear_top_count"] == 1
    assert summary["exact_pair_evaluable_count"] == 1
    assert summary["exact_pair_hit_count"] == 1
    assert summary["exact_pair_hit_rate"] == 1.0
    assert summary["combined_single_evaluable_count"] == 2
    assert summary["combined_single_hit_count"] == 1
    assert summary["combined_single_hit_rate"] == 0.5
    assert summary["home_single_evaluable_count"] == 2
    assert summary["home_single_hit_count"] == 1
    assert summary["home_single_hit_rate"] == 0.5
    assert summary["away_single_evaluable_count"] == 1
    assert summary["away_single_hit_count"] == 1
    assert summary["away_single_hit_rate"] == 1.0
