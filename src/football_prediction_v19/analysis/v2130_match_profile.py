# -*- coding: utf-8 -*-
from __future__ import annotations


def derive_match_profile(distribution: dict[str, object], expected_home: float, expected_away: float) -> str:
    total = expected_home + expected_away
    home = float(distribution["home_win_probability"])
    away = float(distribution["away_win_probability"])
    btts = float(distribution["btts_yes_probability"])
    high = float(distribution["total_goals_4_plus_probability"])
    if total < 2.2 and abs(home - away) < 0.12:
        return "LOW_SCORING_BALANCED"
    if home >= 0.52 and expected_home - expected_away >= 0.45:
        return "HOME_CONTROL"
    if away >= 0.48 and expected_away - expected_home >= 0.35:
        return "AWAY_CONTROL"
    if total >= 3.0 and btts >= 0.58:
        return "OPEN_HIGH_SCORING"
    if high >= 0.38:
        return "HIGH_VARIANCE"
    return "BALANCED_MODERATE"
