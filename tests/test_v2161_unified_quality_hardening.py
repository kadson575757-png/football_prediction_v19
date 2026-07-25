from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from football_prediction_v19.prematch.explanation import build_explanations
from football_prediction_v19.prematch.input_schema import MatchInput
from football_prediction_v19.prematch.match_profile import build_match_profile
from football_prediction_v19.prematch.model_comparison import compare_models
from football_prediction_v19.prematch.unified_runner import analyze_match, run_batch


ROOT = Path(__file__).resolve().parents[1]
PRIMARY = {"HOME": 0.3853, "DRAW": 0.2915, "AWAY": 0.3232}
GOAL_PROBS = {"HOME": 0.5214, "DRAW": 0.2591, "AWAY": 0.2195}


def _features(venue_edge: float = 0.6372, form_edge: float = 0.4) -> dict:
    return {
        "home_venue_points_per_match": 1.5 + venue_edge,
        "away_venue_points_per_match": 1.5,
        "home_last5_points": 1.4 + form_edge,
        "away_last5_points": 1.4,
    }


def _quality() -> dict:
    return {
        "quality_tier": "HIGH", "minimum_team_history": 105,
        "venue_history_ready": True, "fallback_used": False, "asof_clean": True,
    }


def _goal() -> dict:
    return {"expected_home_goals": 1.63, "expected_away_goals": 1.08}


def _history() -> pd.DataFrame:
    rows = []
    teams = ["Alpha", "Beta", "Gamma", "Delta"]
    for index in range(24):
        home, away = teams[index % 4], teams[(index + 1) % 4]
        rows.append({
            "match_date": f"2025-{index // 4 + 1:02d}-{index % 4 * 5 + 1:02d}",
            "competition": "Stub League", "season": "2025/26",
            "home_team": home, "away_team": away,
            "actual_home_goals": (index + 1) % 4, "actual_away_goals": index % 3,
        })
    return pd.DataFrame(rows)


def test_positive_edges_only_create_home_factors():
    explanation = build_explanations(_features(), _goal(), _quality(), PRIMARY, compare_models(PRIMARY, GOAL_PROBS))
    assert {factor["feature_name"] for factor in explanation["top_home_factors"]} == {"venue_ppg_edge", "recent_points_edge"}
    assert explanation["top_away_factors"] == []
    assert explanation["top_draw_factors"] == []


def test_negative_edges_only_create_away_factors_with_absolute_magnitude():
    explanation = build_explanations(_features(-0.6372, -0.4), _goal(), _quality(), PRIMARY)
    assert explanation["top_home_factors"] == []
    assert {factor["feature_name"] for factor in explanation["top_away_factors"]} == {"venue_ppg_edge", "recent_points_edge"}
    assert all(factor["magnitude"] > 0 for factor in explanation["top_away_factors"])


def test_neutral_edges_create_draw_factors_without_directional_claims():
    explanation = build_explanations(_features(0.03, -0.02), _goal(), _quality(), PRIMARY)
    assert explanation["top_home_factors"] == explanation["top_away_factors"] == []
    assert len(explanation["top_draw_factors"]) == 2


def test_quality_and_uncertainty_are_separated():
    explanation = build_explanations(_features(), _goal(), _quality(), PRIMARY)
    quality_names = {factor["feature_name"] for factor in explanation["quality_factors"]}
    uncertainty_names = {factor["feature_name"] for factor in explanation["uncertainty_factors"]}
    assert "established_history" in quality_names
    assert "established_history" not in uncertainty_names
    assert "primary_probability_edge" in uncertainty_names


@pytest.mark.parametrize(
    ("goal", "expected"),
    [
        ({"HOME": 0.42, "DRAW": 0.29, "AWAY": 0.29}, "NONE"),
        ({"HOME": 0.50, "DRAW": 0.27, "AWAY": 0.23}, "LOW"),
        ({"HOME": 0.56, "DRAW": 0.24, "AWAY": 0.20}, "MEDIUM"),
        ({"HOME": 0.32, "DRAW": 0.34, "AWAY": 0.34}, "MEDIUM"),
        ({"HOME": 0.15, "DRAW": 0.20, "AWAY": 0.65}, "HIGH"),
    ],
)
def test_conflict_thresholds(goal, expected):
    assert compare_models(PRIMARY, goal)["conflict_level"] == expected


def test_profile_contains_auditable_rules():
    profile = build_match_profile(PRIMARY, _goal())
    names = {row["profile_rule_name"] for row in profile["profile_rule_audit"]}
    assert {"likely_game_state", "balance_level", "variance_and_goal_timing"} <= names
    assert all({"input_values", "thresholds", "resulting_label"} <= row.keys() for row in profile["profile_rule_audit"])


def test_canonical_schema_report_and_probability_regression(tmp_path):
    match = MatchInput("Stub League", "2025/26", "Alpha", "Beta", "2025-07-10")
    result = analyze_match(match, project_root=ROOT, output_base=tmp_path, history=_history(), strict_asof=True)
    assert result["schema_version"] == "1.1.0"
    assert "winner_prediction" in result and "primary_winner_prediction" not in result
    assert "goal_prediction" in result and "goal_distribution" not in result
    assert "explanation" in result and "explanations" not in result
    assert sum(result["winner_prediction"]["probabilities"].values()) == pytest.approx(1.0, abs=1e-12)
    assert sum(result["goal_prediction"]["outcome_probabilities"].values()) == pytest.approx(1.0, abs=1e-12)
    assert result["asof_audit"]["post_match_rows_used_count"] == 0
    markdown = (Path(result["output_dir"]) / "report.md").read_text(encoding="utf-8")
    assert "%" in markdown
    assert "Primary model" in markdown
    assert "Quality:" in markdown and "Uncertainty:" in markdown
    assert all(value is False for value in result["safety"].values())


def test_batch_remains_ready(tmp_path):
    rows = [
        MatchInput("Stub League", "2025/26", "Alpha", "Beta", "2025-07-10"),
        MatchInput("Stub League", "2025/26", "Gamma", "Delta", "2025-07-11"),
        MatchInput("Stub League", "2025/26", "Beta", "Gamma", "2025-07-12"),
    ]
    result = run_batch(rows, project_root=ROOT, output_base=tmp_path, history=_history(), strict_asof=True)
    assert result["status"] == "READY"
    assert result["successful_count"] == 3
    assert result["failed_count"] == 0
