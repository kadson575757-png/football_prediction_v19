# -*- coding: utf-8 -*-
from __future__ import annotations

from football_prediction_v19.analysis.v19_transition_classifier_preview import V19TransitionClassifier, V19TransitionClassifierConfig


def test_classifier_detects_matched_transition() -> None:
    scenario = {"scenario_id": "S", "expected_final_decision_class": "BET_CANDIDATE_PREVIEW", "expected_promotion_allowed": True, "expected_conflict_score": "MEDIUM"}
    actual = {"final_decision_class": "BET_CANDIDATE_PREVIEW", "promotion_allowed": True, "conflict_score": "MEDIUM"}
    result = V19TransitionClassifier(V19TransitionClassifierConfig(scenario=scenario, actual_override=actual)).run()
    assert result.classification_status == "PASSED"


def test_classifier_detects_mismatched_final_class() -> None:
    scenario = {"scenario_id": "S", "expected_final_decision_class": "BET_CANDIDATE_PREVIEW", "expected_promotion_allowed": True, "expected_conflict_score": "MEDIUM"}
    actual = {"final_decision_class": "ANALYST_LEAN_ONLY", "promotion_allowed": True, "conflict_score": "MEDIUM"}
    result = V19TransitionClassifier(V19TransitionClassifierConfig(scenario=scenario, actual_override=actual)).run()
    assert result.classification_status == "FAILED"
    assert result.transition_matched is False


def test_classifier_detects_promotion_mismatch() -> None:
    scenario = {"scenario_id": "S", "expected_final_decision_class": "BET_CANDIDATE_PREVIEW", "expected_promotion_allowed": True, "expected_conflict_score": "MEDIUM"}
    actual = {"final_decision_class": "BET_CANDIDATE_PREVIEW", "promotion_allowed": False, "conflict_score": "MEDIUM"}
    result = V19TransitionClassifier(V19TransitionClassifierConfig(scenario=scenario, actual_override=actual)).run()
    assert result.classification_status == "FAILED"
    assert result.promotion_matched is False


def test_classifier_outputs_review_required_for_unexpected_conflict() -> None:
    scenario = {"scenario_id": "S", "expected_final_decision_class": "BET_CANDIDATE_PREVIEW", "expected_promotion_allowed": True, "expected_conflict_score": "MEDIUM"}
    actual = {"final_decision_class": "BET_CANDIDATE_PREVIEW", "promotion_allowed": True, "conflict_score": "HIGH"}
    result = V19TransitionClassifier(V19TransitionClassifierConfig(scenario=scenario, actual_override=actual)).run()
    assert result.classification_status == "REVIEW_REQUIRED"
    assert result.conflict_matched is False


def test_classifier_never_enables_stake_or_roi() -> None:
    scenario = {"scenario_id": "S", "expected_final_decision_class": "ANALYST_LEAN_ONLY", "expected_promotion_allowed": False, "expected_conflict_score": "HIGH"}
    actual = {"final_decision_class": "ANALYST_LEAN_ONLY", "promotion_allowed": False, "conflict_score": "HIGH"}
    result = V19TransitionClassifier(V19TransitionClassifierConfig(scenario=scenario, actual_override=actual)).run()
    assert result.staking_logic_enabled is False
    assert result.roi_logic_enabled is False
