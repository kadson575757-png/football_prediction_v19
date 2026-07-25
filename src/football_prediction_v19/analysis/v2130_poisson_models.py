# -*- coding: utf-8 -*-
from __future__ import annotations

import math

import pandas as pd


MODEL_NAMES = [
    "ROLLING_LEAGUE_MEAN_POISSON",
    "ROLLING_ATTACK_DEFENSE_POISSON",
    "ROLLING_ATTACK_DEFENSE_FORM_5_POISSON",
    "ROLLING_ATTACK_DEFENSE_FORM_10_POISSON",
    "VENUE_ATTACK_DEFENSE_POISSON",
    "DIXON_COLES_LOW_SCORE_RHO_M005",
    "DIXON_COLES_LOW_SCORE_RHO_M010",
]


def _clip(value: float) -> float:
    return max(0.2, min(float(value), 4.5))


def expected_goals_for_model(features: pd.Series | dict[str, object], model_name: str) -> tuple[float, float, float]:
    get = features.get
    league_home = float(get("league_home_goals_mean", 1.45))
    league_away = float(get("league_away_goals_mean", 1.15))
    if model_name == "ROLLING_LEAGUE_MEAN_POISSON":
        return _clip(league_home), _clip(league_away), 0.0
    home_attack = float(get("home_attack_strength", 1.0))
    home_defense = float(get("home_defense_strength", 1.0))
    away_attack = float(get("away_attack_strength", 1.0))
    away_defense = float(get("away_defense_strength", 1.0))
    home_xg = league_home * home_attack * away_defense
    away_xg = league_away * away_attack * home_defense
    if "FORM_5" in model_name:
        home_xg *= float(get("home_form5_attack_factor", 1.0))
        away_xg *= float(get("away_form5_attack_factor", 1.0))
    elif "FORM_10" in model_name:
        home_xg *= float(get("home_form10_attack_factor", 1.0))
        away_xg *= float(get("away_form10_attack_factor", 1.0))
    elif model_name == "VENUE_ATTACK_DEFENSE_POISSON":
        if bool(get("venue_history_ready", False)):
            home_xg = league_home * float(get("home_venue_attack_strength", home_attack)) * float(
                get("away_venue_defense_strength", away_defense)
            )
            away_xg = league_away * float(get("away_venue_attack_strength", away_attack)) * float(
                get("home_venue_defense_strength", home_defense)
            )
    rho = -0.05 if model_name.endswith("M005") else -0.10 if model_name.endswith("M010") else 0.0
    return _clip(home_xg), _clip(away_xg), rho


def poisson_deviance(actual: float, predicted: float) -> float:
    predicted = max(float(predicted), 1e-12)
    actual = float(actual)
    return 2.0 * (predicted - actual + (actual * math.log(actual / predicted) if actual > 0 else 0.0))
