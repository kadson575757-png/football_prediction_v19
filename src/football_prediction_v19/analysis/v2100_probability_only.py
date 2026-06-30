# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any


OUTCOMES = ("HOME", "DRAW", "AWAY")


def normalize_probabilities(home: object, draw: object, away: object) -> tuple[float, float, float]:
    values = [_num(home), _num(draw), _num(away)]
    total = sum(values)
    if total <= 0:
        return 0.34, 0.32, 0.34
    return tuple(round(value / total, 4) for value in values)  # type: ignore[return-value]


def build_probability_only_fields(result: dict[str, Any]) -> dict[str, Any]:
    home, draw, away = normalize_probabilities(
        result.get("home_win_probability", result.get("base_home_win_probability", 0.0)),
        result.get("draw_probability", result.get("base_draw_probability", 0.0)),
        result.get("away_win_probability", result.get("base_away_probability", 0.0)),
    )
    base_home, base_draw, base_away = normalize_probabilities(
        result.get("base_home_win_probability", home),
        result.get("base_draw_probability", draw),
        result.get("base_away_probability", away),
    )
    ranked = sorted(zip(OUTCOMES, [home, draw, away], strict=True), key=lambda item: item[1], reverse=True)
    top_outcome = ranked[0][0]
    edge = round(ranked[0][1] - ranked[1][1], 4)
    source_quality = str(result.get("source_quality_band", result.get("data_quality_band", "LOW")) or "LOW").upper()
    missing_context = _missing_context(result)
    uncertainty = _uncertainty_level(edge, source_quality, missing_context)
    data_quality = _data_quality_band(source_quality, missing_context)
    status = "READY" if any(value > 0 for value in [home, draw, away]) else "INSUFFICIENT_SOURCE_DATA"
    if status == "READY" and (uncertainty == "HIGH" or missing_context):
        status = "READY_WITH_LIMITATIONS"
    fields = {
        "winner_analysis_status": "READY",
        "probability_model_status": status,
        "home_win_probability": home,
        "draw_probability": draw,
        "away_win_probability": away,
        "base_home_win_probability": base_home,
        "base_draw_probability": base_draw,
        "base_away_probability": base_away,
        "top_probability_outcome": top_outcome,
        "probability_edge": edge,
        "probability_edge_band": probability_edge_band(edge),
        "uncertainty_level": uncertainty,
        "data_quality_band": data_quality,
        "probability_explanation_status": "READY_WITH_LIMITATIONS" if status != "READY" else "READY",
    }
    fields.update(build_probability_explanations({**result, **fields}, missing_context))
    fields["probability_summary"] = probability_summary(fields)
    fields["data_quality_notes"] = data_quality_notes(result, missing_context)
    return fields


def probability_edge_band(edge: object) -> str:
    value = _num(edge)
    if value < 0.03:
        return "VERY_SMALL"
    if value < 0.07:
        return "SMALL"
    if value < 0.12:
        return "MEDIUM"
    return "LARGE"


def build_probability_explanations(result: dict[str, Any], missing_context: list[str] | None = None) -> dict[str, str]:
    missing = _missing_context(result) if missing_context is None else missing_context
    home = _num(result.get("base_home_win_probability", result.get("home_win_probability", 0.0)))
    draw = _num(result.get("base_draw_probability", result.get("draw_probability", 0.0)))
    away = _num(result.get("base_away_probability", result.get("away_win_probability", 0.0)))
    top = str(result.get("top_probability_outcome", _top_outcome(home, draw, away)))
    edge = _num(result.get("probability_edge", 0.0))
    alignment, conflict = _alignment_summary(result, top)
    return {
        "base_probability_explanation": f"Base model gives Home {_pct(home)}, Draw {_pct(draw)}, Away {_pct(away)}.",
        "ppg_shadow_explanation": _shadow_text("Home/Away PPG", result.get("home_away_ppg_diff"), result.get("ppg_indicator_quality")),
        "last5_shadow_explanation": _shadow_text("Last-5 form", result.get("last5_points_diff"), result.get("last5_indicator_quality")),
        "goal_difference_shadow_explanation": _shadow_text("Goal difference before match", result.get("goal_difference_diff"), result.get("goal_difference_indicator_quality")),
        "goals_for_shadow_explanation": _shadow_text("Goals For per match", result.get("goals_for_per_match_diff"), result.get("goals_for_indicator_quality")),
        "goals_against_shadow_explanation": _shadow_text("Goals Against per match", result.get("goals_against_advantage_diff"), result.get("goals_against_indicator_quality")),
        "signal_alignment_summary": alignment,
        "signal_conflict_summary": conflict,
        "data_quality_explanation": _data_quality_explanation(missing),
        "probability_explanation": f"{top} is the highest probability outcome with a {_pct(edge)} edge. {alignment} {conflict}",
        "final_probability_explanation": "Final probabilities remain base probabilities. Shadow indicators are shown separately for explanation only.",
    }


def top_probability_hit(top_probability_outcome: object, real_result: object) -> str:
    top = str(top_probability_outcome)
    real = str(real_result)
    if top not in OUTCOMES:
        return "RESULT_UNKNOWN"
    if real == "RESULT_UNKNOWN" or not real:
        return "RESULT_UNKNOWN"
    expected = {"HOME": "HOME_WIN", "DRAW": "DRAW", "AWAY": "AWAY_WIN"}[top]
    return "HIT" if real == expected else "MISS"


def probability_summary(result: dict[str, Any]) -> str:
    top = str(result.get("top_probability_outcome", _top_outcome(_num(result.get("home_win_probability")), _num(result.get("draw_probability")), _num(result.get("away_win_probability")))))
    return (
        f"{top} has the highest probability at {_pct(result.get(_outcome_probability_key(top), 0.0))}. "
        f"Home is {_pct(result.get('home_win_probability', 0.0))}, Draw is {_pct(result.get('draw_probability', 0.0))}, "
        f"Away is {_pct(result.get('away_win_probability', 0.0))}. "
        f"The edge is {_pct(result.get('probability_edge', 0.0))}. "
        f"Uncertainty is {str(result.get('uncertainty_level', 'HIGH')).lower()}."
    )


def data_quality_notes(result: dict[str, Any], missing_context: list[str] | None = None) -> list[str]:
    missing = _missing_context(result) if missing_context is None else missing_context
    notes: list[str] = []
    if "xG" in missing:
        notes.append("xG unavailable; uncertainty remains high but probabilities are still produced.")
    if "odds" in missing:
        notes.append("Odds unavailable; market context is not included.")
    if "source quality" in missing:
        notes.append("Source quality is limited; probability output remains available with elevated uncertainty.")
    return notes or ["Core source coverage is sufficient for probability explanation."]


def _missing_context(result: dict[str, Any]) -> list[str]:
    missing = []
    if not _truthy(result.get("xg_available", False)):
        missing.append("xG")
    if not _truthy(result.get("odds_available", False)):
        missing.append("odds")
    if str(result.get("source_quality_band", "")).upper() in {"", "LOW"}:
        missing.append("source quality")
    return missing


def _uncertainty_level(edge: float, source_quality: str, missing_context: list[str]) -> str:
    if len(missing_context) >= 2 or source_quality == "LOW" or edge < 0.03:
        return "HIGH"
    if missing_context or source_quality == "MEDIUM" or edge < 0.08:
        return "MEDIUM"
    return "LOW"


def _data_quality_band(source_quality: str, missing_context: list[str]) -> str:
    if source_quality == "HIGH" and not missing_context:
        return "HIGH"
    if source_quality in {"HIGH", "MEDIUM"} and len(missing_context) <= 1:
        return "MEDIUM"
    return "LOW"


def _alignment_summary(result: dict[str, Any], top: str) -> tuple[str, str]:
    directions = {
        "goal difference": _direction(result.get("gd_adjusted_home_win_probability"), result.get("gd_adjusted_away_probability")),
        "goals for": _direction(result.get("gf_adjusted_home_win_probability"), result.get("gf_adjusted_away_probability")),
        "goals against": _direction(result.get("ga_adjusted_home_win_probability"), result.get("ga_adjusted_away_probability")),
    }
    aligned = [name for name, direction in directions.items() if direction == top]
    conflicts = [name for name, direction in directions.items() if direction in {"HOME", "AWAY"} and direction != top]
    align_text = "Signals supporting the top outcome: " + (", ".join(aligned) if aligned else "none clear") + "."
    conflict_text = "Signals in conflict: " + (", ".join(conflicts) if conflicts else "none clear") + "."
    return align_text, conflict_text


def _direction(home: object, away: object) -> str:
    diff = _num(home) - _num(away)
    if diff >= 0.03:
        return "HOME"
    if diff <= -0.03:
        return "AWAY"
    return "DRAW"


def _shadow_text(label: str, value: object, quality: object) -> str:
    quality_text = str(quality or "LOW")
    numeric = _num(value)
    if abs(numeric) < 0.0001:
        return f"{label} is neutral or unavailable; indicator quality is {quality_text}."
    direction = "Home" if numeric > 0 else "Away"
    return f"{label} favors {direction} by {round(abs(numeric), 3)}; indicator quality is {quality_text}."


def _data_quality_explanation(missing: list[str]) -> str:
    if not missing:
        return "Core sources are available, so uncertainty remains controlled. This is still probability output only."
    return f"{' and '.join(missing)} unavailable or limited, so uncertainty remains elevated. Probability output is still produced."


def _outcome_probability_key(outcome: str) -> str:
    return {"HOME": "home_win_probability", "DRAW": "draw_probability", "AWAY": "away_win_probability"}.get(outcome, "home_win_probability")


def _top_outcome(home: float, draw: float, away: float) -> str:
    return sorted(zip(OUTCOMES, [home, draw, away], strict=True), key=lambda item: item[1], reverse=True)[0][0]


def _pct(value: object) -> str:
    return f"{_num(value) * 100:.2f}%"


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
