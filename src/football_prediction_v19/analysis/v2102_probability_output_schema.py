# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any


REQUIRED_PROBABILITY_RUNNER_FIELDS = [
    "probability_analysis_status",
    "probability_model_status",
    "competition",
    "season",
    "home_team",
    "away_team",
    "match_date",
    "top_probability_outcome",
    "probability_edge",
    "probability_edge_band",
    "uncertainty_level",
    "data_quality_band",
    "probability_explanation_status",
    "probability_summary",
    "data_quality_notes",
    "probability_input_signals",
    "home_win_probability",
    "draw_probability",
    "away_win_probability",
    "base_home_win_probability",
    "base_draw_probability",
    "base_away_probability",
    "base_probability_explanation",
    "probability_explanation",
    "data_quality_explanation",
    "final_probability_explanation",
    "signal_alignment_summary",
    "signal_conflict_summary",
    "automatic_betting_enabled",
    "staking_logic_enabled",
    "roi_logic_enabled",
]

OPTIONAL_PROBABILITY_RUNNER_FIELDS = [
    "fixture_resolver_status",
    "fixture_resolver_source",
    "fixture_candidates_count",
    "resolved_match_date",
    "resolver_reason",
    "reversed_fixture_found",
    "alias_matched",
    "as_of_date",
    "post_match_analysis",
    "leakage_warning",
    "asof_guard_status",
    "asof_guard_reason",
    "source_quality_band",
    "xg_available",
    "odds_available",
    "ppg_shadow_explanation",
    "last5_shadow_explanation",
    "goal_difference_shadow_explanation",
    "goals_for_shadow_explanation",
    "goals_against_shadow_explanation",
    "ppg_adjusted_home_win_probability",
    "ppg_adjusted_draw_probability",
    "ppg_adjusted_away_probability",
    "last5_adjusted_home_win_probability",
    "last5_adjusted_draw_probability",
    "last5_adjusted_away_probability",
    "gd_adjusted_home_win_probability",
    "gd_adjusted_draw_probability",
    "gd_adjusted_away_probability",
    "gf_adjusted_home_win_probability",
    "gf_adjusted_draw_probability",
    "gf_adjusted_away_probability",
    "ga_adjusted_home_win_probability",
    "ga_adjusted_draw_probability",
    "ga_adjusted_away_probability",
]

PROBABILITY_RUNNER_OUTPUT_FIELDS = REQUIRED_PROBABILITY_RUNNER_FIELDS + OPTIONAL_PROBABILITY_RUNNER_FIELDS

FORBIDDEN_PROBABILITY_RUNNER_FIELDS = [
    "winner_analysis_status",
    "decision_class",
    "predicted_winner",
    "winner_pick_count",
    "winner_lean_count",
    "no_decision_count",
    "no_decision_rate",
    "data_blocked_count",
    "data_blocked_rate",
    "recommendation_summary",
    "risk_level",
    "prediction_tier",
    "model_status",
    "primary_reasons",
    "risk_notes",
]

FORBIDDEN_PROBABILITY_RUNNER_TEXT_PATTERNS = [
    "NO_DECISION",
    "DATA_BLOCKED",
    "blocked by rule",
    "blocked",
    "no decision",
    "No Decision",
    "Lean-only",
    "decision strength",
    "prediction tier",
    "winner pick",
    "winner lean",
    "Sperre",
    "gesperrt",
    "verboten",
]

REQUIRED_PROBABILITY_EVALUATION_FIELDS = [
    "probability_evaluation_status",
    "matches_requested",
    "matches_evaluated",
    "probability_rows_count",
    "probability_output_rate",
    "top_probability_home_count",
    "top_probability_draw_count",
    "top_probability_away_count",
    "top_probability_hit_count",
    "top_probability_miss_count",
    "top_probability_hit_rate",
    "insufficient_source_data_count",
    "automatic_betting_enabled",
    "staking_logic_enabled",
    "roi_logic_enabled",
]

FORBIDDEN_PROBABILITY_EVALUATION_FIELDS = [
    "decision_count",
    "winner_pick_count",
    "winner_lean_count",
    "no_decision_count",
    "no_decision_rate",
    "data_blocked_count",
    "data_blocked_rate",
]


def validate_probability_runner_output(output: dict[str, Any]) -> dict[str, object]:
    missing = [field for field in REQUIRED_PROBABILITY_RUNNER_FIELDS if field not in output]
    forbidden = [field for field in FORBIDDEN_PROBABILITY_RUNNER_FIELDS if field in output]
    forbidden_patterns = _forbidden_patterns(output, FORBIDDEN_PROBABILITY_RUNNER_TEXT_PATTERNS)
    safety_valid = _safety_flags_false(output)
    status = "READY" if not missing and not forbidden and not forbidden_patterns and safety_valid else "FAILED"
    return {
        "schema_validation_status": status,
        "missing_required_fields": missing,
        "forbidden_fields_present": forbidden,
        "forbidden_text_patterns_present": forbidden_patterns,
        "safety_flags_valid": safety_valid,
    }


def validate_probability_evaluation_output(output: dict[str, Any]) -> dict[str, object]:
    missing = [field for field in REQUIRED_PROBABILITY_EVALUATION_FIELDS if field not in output]
    forbidden = [field for field in FORBIDDEN_PROBABILITY_EVALUATION_FIELDS if field in output and not field.startswith("legacy_")]
    safety_valid = _safety_flags_false(output)
    status = "READY" if not missing and not forbidden and safety_valid else "FAILED"
    return {
        "schema_validation_status": status,
        "missing_required_fields": missing,
        "forbidden_fields_present": forbidden,
        "safety_flags_valid": safety_valid,
    }


def _forbidden_patterns(output: dict[str, Any], patterns: list[str]) -> list[str]:
    text = "\n".join(_stringify(value) for value in output.values())
    return [pattern for pattern in patterns if pattern in text]


def _stringify(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(f"{key} {_stringify(item)}" for key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_stringify(item) for item in value)
    return str(value)


def _safety_flags_false(output: dict[str, Any]) -> bool:
    return all(_is_false(output.get(field)) for field in ["automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled"])


def _is_false(value: Any) -> bool:
    if isinstance(value, bool):
        return value is False
    return str(value).strip().lower() == "false"
