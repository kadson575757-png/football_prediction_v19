from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from football_prediction_v19.analysis.v2181_challenger_unique_oof_audit import (
    SAFETY,
    calibration_audit,
    component_decomposition,
    correction_transition_audit,
    deduplicate_oof,
    draw_failure_audit,
)
from football_prediction_v19.models.model_registry import get_model


def _prediction_rows() -> pd.DataFrame:
    records = []
    fixtures = [
        ("League", "2025/26", "2025-01-01", "A", "B", "HOME"),
        ("League", "2025/26", "2025-01-02", "C", "D", "DRAW"),
        ("League", "2025/26", "2025-01-03", "A", "C", "AWAY"),
    ]
    folds = [
        ("LEAVE_ONE_COMPETITION_OUT", "League", 3),
        ("LEAVE_ONE_SEASON_OUT", "2025/26", 2),
        ("CHRONOLOGICAL_LAST_SEGMENT", "LAST", 1),
    ]
    for fixture in fixtures:
        for fold_type, holdout, fold in folds:
            competition, season, date, home, away, actual = fixture
            row = {
                "competition": competition, "season": season, "match_date": date,
                "home_team": home, "away_team": away, "actual_result": actual,
                "fold_type": fold_type, "outer_holdout": holdout, "outer_fold": fold,
                "expected_home_goals": 1.4, "expected_away_goals": 1.1,
                "rating_difference": 40, "base_probability_edge": .08,
                "model_agreement": 1, "maximum_model_probability_difference": .06,
                "history_quality_numeric": 1.0,
            }
            base = {"HOME": [.50, .28, .22], "DRAW": [.40, .30, .30], "AWAY": [.42, .28, .30]}[actual]
            good = {"HOME": [.60, .23, .17], "DRAW": [.30, .42, .28], "AWAY": [.22, .23, .55]}[actual]
            prefixes = {
                "baseline": base, "rating": good, "hierarchical": good,
                "primary_rating_meta": good, "primary_goal_meta": good,
                "primary_rating_goal_meta": good, "challenger": good,
            }
            for prefix, values in prefixes.items():
                for outcome, value in zip(("home", "draw", "away"), values):
                    row[f"{prefix}_{outcome}_probability"] = value
            records.append(row)
    return pd.DataFrame(records)


def test_fixture_deduplication_uses_deterministic_priority():
    unique, audit, stats = deduplicate_oof(_prediction_rows())
    assert len(unique) == 3
    assert unique["fold_type"].eq("CHRONOLOGICAL_LAST_SEGMENT").all()
    assert audit["prediction_count"].eq(3).all()
    assert stats["raw_holdout_prediction_count"] == 9
    assert stats["maximum_predictions_per_fixture"] == 3


def test_each_fixture_occurs_exactly_once_after_deduplication():
    unique, _, _ = deduplicate_oof(_prediction_rows())
    assert not unique.duplicated(["competition", "season", "match_date", "home_team", "away_team"]).any()


def test_component_decomposition_uses_identical_unique_rows():
    unique, _, _ = deduplicate_oof(_prediction_rows())
    result = component_decomposition(unique)
    assert len(result) == 7
    assert set(result["complexity_level"]) <= {"LOW", "MEDIUM", "HIGH"}
    assert result.loc[result.model_name.eq("MODEL_G_FULL_META_CHALLENGER"), "hit_rate"].iloc[0] == 1


def test_draw_failure_audit_contains_rank_and_segment_summaries():
    unique, _, _ = deduplicate_oof(_prediction_rows())
    result = draw_failure_audit(unique)
    fixtures = result[result.record_type.eq("FIXTURE")]
    assert fixtures["draw_probability_rank"].between(1, 3).all()
    assert {"OVERALL", "COMPETITION", "EXPECTED_GOALS"} <= set(result.get("group_type", pd.Series()).dropna())


def test_correction_transition_matrix_accounts_for_all_rows():
    unique, _, _ = deduplicate_oof(_prediction_rows())
    matrix, details = correction_transition_audit(unique)
    assert matrix["count"].sum() == len(unique)
    assert details["newly_corrected"].sum() >= 0
    assert details["newly_broken"].sum() >= 0


def test_calibration_buckets_and_summaries_are_finite():
    unique, _, _ = deduplicate_oof(_prediction_rows())
    result = calibration_audit(unique)
    summaries = result[result.record_type.eq("SUMMARY")]
    assert set(summaries["model"]) == {"BASELINE", "CHALLENGER"}
    assert np.isfinite(summaries["expected_calibration_error"]).all()
    assert result[result.record_type.eq("BUCKET")]["absolute_error"].between(0, 1).all()


def test_shadow_registry_and_primary_authority_are_separate():
    shadow = get_model("PRIMARY_PLUS_RATING_META_V2182")
    primary = get_model("PRIMARY_WINNER_V21_RESULTS_CORE")
    assert shadow["status"] == "SHADOW_APPROVED"
    assert shadow["role"] == "SHADOW_WINNER_CHALLENGER"
    assert shadow["authoritative_for_1x2"] is False
    assert shadow["probability_blending_enabled"] is False
    assert shadow["known_limitation"] == "DRAW_RECALL_LOW"
    assert primary["status"] == "ACTIVE"
    assert primary["role"] == "PRIMARY_WINNER"


def test_safety_flags_and_script_core_exist():
    assert all(value is False for value in SAFETY.values())
    root = Path(__file__).resolve().parents[1]
    assert (root / "scripts/run_v2181_challenger_unique_oof_audit.py").exists()
    assert (root / "src/football_prediction_v19/analysis/v2181_challenger_unique_oof_audit.py").exists()
