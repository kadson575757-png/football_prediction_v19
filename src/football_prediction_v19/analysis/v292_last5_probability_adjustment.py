# -*- coding: utf-8 -*-
from __future__ import annotations


def apply_last5_form_shadow_adjustment(
    base_home_probability: float,
    base_draw_probability: float,
    base_away_probability: float,
    last5_indicator: dict[str, object],
) -> dict[str, object]:
    base_home = _num(base_home_probability)
    base_draw = _num(base_draw_probability)
    base_away = _num(base_away_probability)
    if base_home + base_draw + base_away <= 0:
        return _result(base_home, base_draw, base_away, 0.0, False, "Base probabilities unavailable; no Last-5 adjustment", last5_indicator)
    quality = str(last5_indicator.get("last5_indicator_quality", "LOW"))
    diff = _num(last5_indicator.get("last5_points_diff", 0.0))
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
    reason = "LOW quality Last-5 form; no adjustment" if quality == "LOW" else ("Last-5 points diff below threshold; no adjustment" if not applied else "Last-5 points differential shifted probability mass between Home and Away")
    return _result(base_home, base_draw, base_away, strength, applied, reason, last5_indicator, adjusted_home, adjusted_draw, adjusted_away)


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
        "last5_adjusted_home_win_probability": round(base_home if adjusted_home is None else adjusted_home, 4),
        "last5_adjusted_draw_probability": round(base_draw if adjusted_draw is None else adjusted_draw, 4),
        "last5_adjusted_away_probability": round(base_away if adjusted_away is None else adjusted_away, 4),
        "last5_adjustment_applied": bool(applied),
        "last5_adjustment_strength": round(strength, 4),
        "last5_adjustment_reason": reason,
        "home_last5_points": indicator.get("home_last5_points", 0),
        "away_last5_points": indicator.get("away_last5_points", 0),
        "home_last5_points_per_match": indicator.get("home_last5_points_per_match", 0.0),
        "away_last5_points_per_match": indicator.get("away_last5_points_per_match", 0.0),
        "last5_points_diff": indicator.get("last5_points_diff", 0),
        "last5_indicator_quality": indicator.get("last5_indicator_quality", "LOW"),
    }


def _strength(diff: float) -> float:
    value = abs(diff)
    if value < 3:
        return 0.0
    if value < 6:
        return 0.01
    if value < 9:
        return 0.025
    return 0.04


def _num(value: object) -> float:
    try:
        if str(value).strip() == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
