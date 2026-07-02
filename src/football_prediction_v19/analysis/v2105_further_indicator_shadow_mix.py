# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any

from football_prediction_v19.analysis.v2104_indicator_shadow_common import normalize_probabilities


PREFIX_BY_NAME = {
    "CLEAN_SHEET_FAILED_TO_SCORE_PROFILE": "csfts",
    "REST_DAYS_CONGESTION_PROFILE": "rdc",
    "TABLE_STRENGTH_GAP_PROFILE": "tsg",
    "COMEBACK_BLOWN_LEAD_PROFILE": "cbl",
}


def build_v2105_further_indicator_shadow_mix(
    base_home_probability: float,
    base_draw_probability: float,
    base_away_probability: float,
    indicator_results: list[dict[str, Any]] | dict[str, dict[str, Any]],
    weights: dict[str, float] | None = None,
    max_total_shift: float = 0.06,
) -> dict[str, object]:
    return _build_mix("v2105_mix", base_home_probability, base_draw_probability, base_away_probability, indicator_results, weights, max_total_shift, PREFIX_BY_NAME)


def _build_mix(prefix: str, base_home_probability: float, base_draw_probability: float, base_away_probability: float, indicator_results: list[dict[str, Any]] | dict[str, dict[str, Any]], weights: dict[str, float] | None, max_total_shift: float, prefix_by_name: dict[str, str]) -> dict[str, object]:
    base_home, base_draw, base_away = normalize_probabilities(base_home_probability, base_draw_probability, base_away_probability)
    indicators = list(indicator_results.values()) if isinstance(indicator_results, dict) else list(indicator_results)
    usable = [_normalized_indicator(indicator, prefix_by_name) for indicator in indicators]
    usable = [indicator for indicator in usable if indicator["quality"] in {"FULL", "PARTIAL"} and indicator["applied"]]
    if weights is not None:
        allowed = {name for name, weight in weights.items() if float(weight) > 0}
        usable = [indicator for indicator in usable if indicator["name"] in allowed]
    if not usable:
        return _result(prefix, base_home, base_draw, base_away, [], "no usable FULL/PARTIAL applied indicators", 0.0)
    raw_weights = {indicator["name"]: float(weights.get(indicator["name"], 0.0)) if weights else 1.0 for indicator in usable}
    total_weight = sum(raw_weights.values()) or 1.0
    delta_home = sum((indicator["home"] - base_home) * raw_weights[indicator["name"]] for indicator in usable) / total_weight
    delta_draw = sum((indicator["draw"] - base_draw) * raw_weights[indicator["name"]] for indicator in usable) / total_weight
    delta_away = sum((indicator["away"] - base_away) * raw_weights[indicator["name"]] for indicator in usable) / total_weight
    total_shift = abs(delta_home) + abs(delta_draw) + abs(delta_away)
    if total_shift > max_total_shift and total_shift > 0:
        scale = max_total_shift / total_shift
        delta_home *= scale
        delta_draw *= scale
        delta_away *= scale
        total_shift = max_total_shift
    home, draw, away = normalize_probabilities(base_home + delta_home, base_draw + delta_draw, base_away + delta_away)
    return _result(prefix, home, draw, away, [indicator["name"] for indicator in usable], "weighted_average_deltas" if weights else "equal_weight_average_deltas", total_shift)


def _normalized_indicator(indicator: dict[str, Any], prefix_by_name: dict[str, str]) -> dict[str, Any]:
    name = str(indicator.get("indicator_name") or _name_from_prefix(indicator, prefix_by_name))
    short = prefix_by_name.get(name, "")
    return {
        "name": name,
        "quality": str(indicator.get("indicator_quality", indicator.get(f"{short}_indicator_quality", "LOW"))),
        "applied": _truthy(indicator.get("adjustment_applied", indicator.get(f"{short}_adjustment_applied", False))),
        "home": _num(indicator.get("adjusted_home_win_probability", indicator.get(f"{short}_adjusted_home_win_probability", 0.0))),
        "draw": _num(indicator.get("adjusted_draw_probability", indicator.get(f"{short}_adjusted_draw_probability", 0.0))),
        "away": _num(indicator.get("adjusted_away_probability", indicator.get(f"{short}_adjusted_away_probability", 0.0))),
    }


def _name_from_prefix(indicator: dict[str, Any], prefix_by_name: dict[str, str]) -> str:
    for name, short in prefix_by_name.items():
        if f"{short}_indicator_quality" in indicator:
            return name
    return "UNKNOWN"


def _result(prefix: str, home: float, draw: float, away: float, included: list[str], strategy: str, total_shift: float) -> dict[str, object]:
    top = max({"HOME": home, "DRAW": draw, "AWAY": away}.items(), key=lambda item: item[1])[0]
    return {
        f"{prefix}_indicator_count": len(included),
        f"{prefix}_included_indicators": "|".join(included),
        f"{prefix}_strategy": strategy,
        f"{prefix}_adjusted_home_win_probability": round(home, 4),
        f"{prefix}_adjusted_draw_probability": round(draw, 4),
        f"{prefix}_adjusted_away_probability": round(away, 4),
        f"{prefix}_total_shift": round(total_shift, 4),
        f"{prefix}_top_probability_outcome": top,
        f"{prefix}_shadow_explanation": "No usable indicator shadows for mix." if not included else f"Mixed {len(included)} indicator shadows: {', '.join(included)}.",
    }


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _num(value: object) -> float:
    try:
        if str(value).strip() == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
