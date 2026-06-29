# -*- coding: utf-8 -*-
from __future__ import annotations


def apply_goals_for_shadow_adjustment(
    base_home_probability: float,
    base_draw_probability: float,
    base_away_probability: float,
    goals_for_indicator: dict[str, object],
) -> dict[str, object]:
    base_home = _num(base_home_probability)
    base_draw = _num(base_draw_probability)
    base_away = _num(base_away_probability)
    if base_home + base_draw + base_away <= 0:
        return _result(base_home, base_draw, base_away, 0.0, False, "Base probabilities unavailable; no Goals For adjustment", goals_for_indicator)
    quality = str(goals_for_indicator.get("goals_for_indicator_quality", "LOW"))
    diff = _num(goals_for_indicator.get("goals_for_per_match_diff", 0.0))
    strength = _strength(diff) if quality != "LOW" else 0.0
    home = base_home
    draw = base_draw
    away = base_away
    applied = strength > 0
    if applied and diff > 0:
        home += strength
        away -= strength
    elif applied and diff < 0:
        away += strength
        home -= strength
    home = max(0.01, home)
    away = max(0.01, away)
    draw = max(0.01, draw)
    total = home + draw + away
    adjusted_home = round(home / total, 4)
    adjusted_draw = round(draw / total, 4)
    adjusted_away = round(max(0.0, 1.0 - adjusted_home - adjusted_draw), 4)
    reason = "LOW quality Goals For per match; no adjustment" if quality == "LOW" else ("Goals For per match diff below threshold; no adjustment" if not applied else "Goals For per match differential shifted probability mass between Home and Away")
    return _result(base_home, base_draw, base_away, strength, applied, reason, goals_for_indicator, adjusted_home, adjusted_draw, adjusted_away)


def _result(
    base_home: float,
    base_draw: float,
    base_away: float,
    strength: float,
    applied: bool,
    reason: str,
    indicator: dict[str, object],
    adjusted_home: float | None = None,
    adjusted_draw: float | None = None,
    adjusted_away: float | None = None,
) -> dict[str, object]:
    return {
        "gf_adjusted_home_win_probability": round(base_home if adjusted_home is None else adjusted_home, 4),
        "gf_adjusted_draw_probability": round(base_draw if adjusted_draw is None else adjusted_draw, 4),
        "gf_adjusted_away_probability": round(base_away if adjusted_away is None else adjusted_away, 4),
        "gf_adjustment_applied": bool(applied),
        "gf_adjustment_strength": round(strength, 4),
        "gf_adjustment_reason": reason,
        "home_goals_for_before_match": indicator.get("home_goals_for_before_match", 0),
        "away_goals_for_before_match": indicator.get("away_goals_for_before_match", 0),
        "home_goals_for_per_match_before_match": indicator.get("home_goals_for_per_match_before_match", 0.0),
        "away_goals_for_per_match_before_match": indicator.get("away_goals_for_per_match_before_match", 0.0),
        "goals_for_per_match_diff": indicator.get("goals_for_per_match_diff", 0.0),
        "goals_for_indicator_quality": indicator.get("goals_for_indicator_quality", "LOW"),
    }


def _strength(diff: float) -> float:
    value = abs(diff)
    if value < 0.20:
        return 0.0
    if value < 0.45:
        return 0.01
    if value < 0.75:
        return 0.025
    return 0.04


def _num(value: object) -> float:
    try:
        if str(value).strip() == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
