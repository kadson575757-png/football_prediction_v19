# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v2130_match_profile import derive_match_profile
from football_prediction_v19.analysis.v2130_score_matrix import build_score_matrix, derive_distribution


LAMBDA_MIN = 0.15
LAMBDA_MAX = 4.50
BASELINE = "LEAGUE_MEAN_BASELINE"


def candidate_configurations() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = [{"model_name": BASELINE, "family": BASELINE, "shrinkage_weight": 0, "form_window": 0, "form_weight": 0.0, "rho": 0.0}]
    for weight in (5, 10, 20):
        for family in ("SHRUNK_ATTACK_DEFENSE", "SHRUNK_ATTACK_DEFENSE_VENUE", "SHRUNK_ATTACK_DEFENSE_OPPONENT"):
            rows.append({"model_name": f"{family}_S{weight}", "family": family, "shrinkage_weight": weight, "form_window": 0, "form_weight": 0.0, "rho": 0.0})
    for window in (5, 10):
        for influence in (0.10, 0.20):
            rows.append({
                "model_name": f"SHRUNK_ATTACK_DEFENSE_VENUE_FORM_S10_W{window}_F{int(influence*100):02d}",
                "family": "SHRUNK_ATTACK_DEFENSE_VENUE_FORM", "shrinkage_weight": 10,
                "form_window": window, "form_weight": influence, "rho": 0.0,
            })
    for rho in (-0.05, -0.10):
        rows.append({
            "model_name": f"DIXON_COLES_ON_BEST_BASE_S10_RHO_{str(abs(rho)).replace('.', '')}",
            "family": "DIXON_COLES_ON_BEST_BASE", "shrinkage_weight": 10,
            "form_window": 0, "form_weight": 0.0, "rho": rho,
        })
    return rows


def shrunk_rate(observed_rate: float, history_count: int, league_rate: float, shrinkage_weight: int) -> float:
    if history_count <= 0:
        return float(league_rate)
    return (history_count * float(observed_rate) + shrinkage_weight * float(league_rate)) / (history_count + shrinkage_weight)


def repaired_lambdas(feature: pd.Series | dict[str, object], config: dict[str, object]) -> dict[str, object]:
    get = feature.get
    league_home = float(get("league_home_goals_mean", 1.45))
    league_away = float(get("league_away_goals_mean", 1.15))
    league_team = (league_home + league_away) / 2
    family = str(config["family"])
    if family == BASELINE:
        raw_home, raw_away = league_home, league_away
        home_source = away_source = "LEAGUE_MEAN"
    else:
        weight = int(config["shrinkage_weight"])
        hc, ac = int(get("home_prior_matches_count", 0)), int(get("away_prior_matches_count", 0))
        home_attack = shrunk_rate(float(get("home_attack_strength", 1)) * league_team, hc, league_team, weight) / league_team
        home_defense = shrunk_rate(float(get("home_defense_strength", 1)) * league_team, hc, league_team, weight) / league_team
        away_attack = shrunk_rate(float(get("away_attack_strength", 1)) * league_team, ac, league_team, weight) / league_team
        away_defense = shrunk_rate(float(get("away_defense_strength", 1)) * league_team, ac, league_team, weight) / league_team
        raw_home, raw_away = league_home * home_attack * away_defense, league_away * away_attack * home_defense
        home_source = "OVERALL_TEAM_HISTORY" if hc >= 5 else "PREVIOUS_SEASON_OR_LEAGUE_SHRINKAGE"
        away_source = "OVERALL_TEAM_HISTORY" if ac >= 5 else "PREVIOUS_SEASON_OR_LEAGUE_SHRINKAGE"
        if "VENUE" in family and bool(get("venue_history_ready", False)):
            venue_home = league_home * float(get("home_venue_attack_strength", 1)) * float(get("away_venue_defense_strength", 1))
            venue_away = league_away * float(get("away_venue_attack_strength", 1)) * float(get("home_venue_defense_strength", 1))
            raw_home = 0.5 * raw_home + 0.5 * venue_home
            raw_away = 0.5 * raw_away + 0.5 * venue_away
            home_source = away_source = "VENUE_TEAM_HISTORY"
        if family == "SHRUNK_ATTACK_DEFENSE_OPPONENT":
            # Deterministic one-step opponent normalization, bounded to prevent feedback explosion.
            raw_home *= max(0.85, min(1 / max(away_defense, 0.2), 1.15))
            raw_away *= max(0.85, min(1 / max(home_defense, 0.2), 1.15))
        if family == "SHRUNK_ATTACK_DEFENSE_VENUE_FORM":
            window, influence = int(config["form_window"]), float(config["form_weight"])
            raw_home *= (1 - influence) + influence * float(get(f"home_form{window}_attack_factor", 1))
            raw_away *= (1 - influence) + influence * float(get(f"away_form{window}_attack_factor", 1))
        if family == "DIXON_COLES_ON_BEST_BASE":
            pass
    home = max(LAMBDA_MIN, min(raw_home, LAMBDA_MAX))
    away = max(LAMBDA_MIN, min(raw_away, LAMBDA_MAX))
    reason = "" if home_source in ("OVERALL_TEAM_HISTORY", "VENUE_TEAM_HISTORY") and away_source in ("OVERALL_TEAM_HISTORY", "VENUE_TEAM_HISTORY") else "LOW_OR_MISSING_TEAM_HISTORY"
    return {
        "raw_expected_home_goals": raw_home, "raw_expected_away_goals": raw_away,
        "expected_home_goals": home, "expected_away_goals": away,
        "lambda_home_clipped": home != raw_home, "lambda_away_clipped": away != raw_away,
        "home_feature_source": home_source, "away_feature_source": away_source,
        "fallback_reason": reason,
        "opponent_adjustment_available": family == "SHRUNK_ATTACK_DEFENSE_OPPONENT",
        "form_available": family == "SHRUNK_ATTACK_DEFENSE_VENUE_FORM",
    }


def generate_repaired_predictions(features: pd.DataFrame) -> pd.DataFrame:
    records = []
    for _, feature in features.iterrows():
        for config in candidate_configurations():
            lambdas = repaired_lambdas(feature, config)
            max_goals = 8
            matrix, residual = build_score_matrix(
                lambdas["expected_home_goals"], lambdas["expected_away_goals"],
                max_goals=max_goals, rho=float(config["rho"]),
            )
            while residual >= 1e-8 and max_goals < 24:
                max_goals += 2
                matrix, residual = build_score_matrix(
                    lambdas["expected_home_goals"], lambdas["expected_away_goals"],
                    max_goals=max_goals, rho=float(config["rho"]),
                )
            distribution = derive_distribution(matrix)
            record = feature.to_dict()
            record.update(config)
            record.update(lambdas)
            record.update(distribution)
            record.update({
                "expected_total_goals": lambdas["expected_home_goals"] + lambdas["expected_away_goals"],
                "matrix_max_goals": max_goals, "matrix_residual_mass": residual,
                "probability_valid": abs(float(distribution["probability_sum"]) - 1) <= 1e-12 and residual < 1e-8,
                "match_profile": derive_match_profile(
                    distribution, lambdas["expected_home_goals"], lambdas["expected_away_goals"]
                ),
            })
            records.append(record)
    return pd.DataFrame(records)
