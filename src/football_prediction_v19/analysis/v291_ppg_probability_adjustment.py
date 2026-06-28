# -*- coding: utf-8 -*-
from __future__ import annotations


def apply_home_away_ppg_adjustment(
    base_home_probability: float,
    base_draw_probability: float,
    base_away_probability: float,
    ppg_indicator: dict[str, object],
) -> dict[str, object]:
    base_home = _num(base_home_probability)
    base_draw = _num(base_draw_probability)
    base_away = _num(base_away_probability)
    if base_home + base_draw + base_away <= 0:
        quality = str(ppg_indicator.get("indicator_quality", "LOW"))
        return {
            "base_home_win_probability": 0.0,
            "base_draw_probability": 0.0,
            "base_away_probability": 0.0,
            "base_away_win_probability": 0.0,
            "adjusted_home_win_probability": 0.0,
            "adjusted_draw_probability": 0.0,
            "adjusted_away_win_probability": 0.0,
            "ppg_adjustment_applied": False,
            "ppg_adjustment_strength": 0.0,
            "ppg_adjustment_reason": "Base probabilities unavailable; no PPG adjustment",
            "home_home_ppg_before_match": ppg_indicator.get("home_home_ppg_before_match", 0.0),
            "away_away_ppg_before_match": ppg_indicator.get("away_away_ppg_before_match", 0.0),
            "home_away_ppg_diff": ppg_indicator.get("home_away_ppg_diff", 0.0),
            "ppg_indicator_quality": quality,
        }
    diff = _num(ppg_indicator.get("home_away_ppg_diff", 0.0))
    quality = str(ppg_indicator.get("indicator_quality", "LOW"))
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
    reason = "LOW quality Home/Away PPG; no adjustment" if quality == "LOW" else ("PPG diff below threshold; no adjustment" if not applied else "Home/Away PPG shifted probability mass between Home and Away")
    return {
        "base_home_win_probability": round(base_home, 4),
        "base_draw_probability": round(base_draw, 4),
        "base_away_probability": round(base_away, 4),
        "base_away_win_probability": round(base_away, 4),
        "adjusted_home_win_probability": adjusted_home,
        "adjusted_draw_probability": adjusted_draw,
        "adjusted_away_win_probability": adjusted_away,
        "ppg_adjustment_applied": bool(applied),
        "ppg_adjustment_strength": round(strength, 4),
        "ppg_adjustment_reason": reason,
        "home_home_ppg_before_match": ppg_indicator.get("home_home_ppg_before_match", 0.0),
        "away_away_ppg_before_match": ppg_indicator.get("away_away_ppg_before_match", 0.0),
        "home_away_ppg_diff": ppg_indicator.get("home_away_ppg_diff", 0.0),
        "ppg_indicator_quality": quality,
    }


def _strength(diff: float) -> float:
    value = abs(diff)
    if value < 0.25:
        return 0.0
    if value < 0.75:
        return 0.01
    if value < 1.25:
        return 0.025
    return 0.04


def _num(value: object) -> float:
    try:
        if str(value).strip() == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
