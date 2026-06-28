# -*- coding: utf-8 -*-
from __future__ import annotations


def apply_goal_difference_shadow_adjustment(
    base_home_probability: float,
    base_draw_probability: float,
    base_away_probability: float,
    goal_difference_indicator: dict[str, object],
) -> dict[str, object]:
    base_home = _num(base_home_probability)
    base_draw = _num(base_draw_probability)
    base_away = _num(base_away_probability)
    if base_home + base_draw + base_away <= 0:
        return _result(base_home, base_draw, base_away, 0.0, False, "Base probabilities unavailable; no goal-difference adjustment", goal_difference_indicator)
    quality = str(goal_difference_indicator.get("goal_difference_indicator_quality", "LOW"))
    diff = _num(goal_difference_indicator.get("goal_difference_diff", 0.0))
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
    reason = "LOW quality goal difference; no adjustment" if quality == "LOW" else ("Goal-difference diff below threshold; no adjustment" if not applied else "Goal-difference differential shifted probability mass between Home and Away")
    return _result(base_home, base_draw, base_away, strength, applied, reason, goal_difference_indicator, adjusted_home, adjusted_draw, adjusted_away)


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
        "gd_adjusted_home_win_probability": round(base_home if adjusted_home is None else adjusted_home, 4),
        "gd_adjusted_draw_probability": round(base_draw if adjusted_draw is None else adjusted_draw, 4),
        "gd_adjusted_away_probability": round(base_away if adjusted_away is None else adjusted_away, 4),
        "gd_adjustment_applied": bool(applied),
        "gd_adjustment_strength": round(strength, 4),
        "gd_adjustment_reason": reason,
        "home_matches_before_match": indicator.get("home_matches_before_match", 0),
        "away_matches_before_match": indicator.get("away_matches_before_match", 0),
        "home_goals_for_before_match": indicator.get("home_goals_for_before_match", 0),
        "home_goals_against_before_match": indicator.get("home_goals_against_before_match", 0),
        "away_goals_for_before_match": indicator.get("away_goals_for_before_match", 0),
        "away_goals_against_before_match": indicator.get("away_goals_against_before_match", 0),
        "home_goal_difference_before_match": indicator.get("home_goal_difference_before_match", 0),
        "away_goal_difference_before_match": indicator.get("away_goal_difference_before_match", 0),
        "goal_difference_diff": indicator.get("goal_difference_diff", 0),
        "goal_difference_indicator_quality": indicator.get("goal_difference_indicator_quality", "LOW"),
    }


def _strength(diff: float) -> float:
    value = abs(diff)
    if value < 5:
        return 0.0
    if value < 10:
        return 0.01
    if value < 20:
        return 0.025
    return 0.04


def _num(value: object) -> float:
    try:
        if str(value).strip() == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
