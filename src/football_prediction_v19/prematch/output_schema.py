"""Stable output schema helpers."""

from __future__ import annotations

import json
from typing import Any


SCHEMA_VERSION = "1.1.0"
RUNNER_VERSION = "v2.16.1"
OUTCOMES = ("HOME", "DRAW", "AWAY")


def normalized_probabilities(values: dict[str, float]) -> dict[str, float]:
    cleaned = {key: max(0.0, float(values[key])) for key in OUTCOMES}
    total = sum(cleaned.values())
    if total <= 0:
        raise ValueError("probability total must be positive")
    result = {key: cleaned[key] / total for key in OUTCOMES}
    result["AWAY"] = 1.0 - result["HOME"] - result["DRAW"]
    return result


def validate_probability_distribution(values: dict[str, float], tolerance: float = 1e-12) -> None:
    if any(not 0.0 <= float(values[key]) <= 1.0 for key in OUTCOMES):
        raise ValueError("probabilities must be in [0, 1]")
    if abs(sum(float(values[key]) for key in OUTCOMES) - 1.0) > tolerance:
        raise ValueError("probabilities must sum to one")


def flatten_prediction(payload: dict[str, Any]) -> dict[str, Any]:
    primary = payload["winner_prediction"]
    goal = payload["goal_prediction"]
    quality = payload["data_quality"]
    return {
        "schema_version": payload["schema_version"],
        **payload["match"],
        "primary_model": primary["model_name"],
        "home_probability": primary["probabilities"]["HOME"],
        "draw_probability": primary["probabilities"]["DRAW"],
        "away_probability": primary["probabilities"]["AWAY"],
        "top_outcome": primary["top_outcome"],
        "confidence_band": primary["confidence_band"],
        "expected_home_goals": goal["expected_home_goals"],
        "expected_away_goals": goal["expected_away_goals"],
        "most_likely_scoreline": goal["most_likely_scoreline"],
        "match_profile": payload["match_profile"]["main_profile"],
        "comparison_conflict": payload["model_comparison"]["conflict_level"],
        "data_quality": quality["quality_tier"],
        "fallback_used": quality["fallback_used"],
        "generated_at": payload["generated_at"],
        "safety_flags": json.dumps(payload["safety"], sort_keys=True),
    }
