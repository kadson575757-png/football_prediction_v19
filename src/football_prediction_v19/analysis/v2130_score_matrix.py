# -*- coding: utf-8 -*-
from __future__ import annotations

import math

import numpy as np


def poisson_pmf(goals: int, expected: float) -> float:
    expected = max(0.05, min(float(expected), 8.0))
    return math.exp(-expected) * expected**goals / math.factorial(goals)


def dixon_coles_tau(home_goals: int, away_goals: int, home_xg: float, away_xg: float, rho: float) -> float:
    if (home_goals, away_goals) == (0, 0):
        return 1.0 - home_xg * away_xg * rho
    if (home_goals, away_goals) == (1, 0):
        return 1.0 + away_xg * rho
    if (home_goals, away_goals) == (0, 1):
        return 1.0 + home_xg * rho
    if (home_goals, away_goals) == (1, 1):
        return 1.0 - rho
    return 1.0


def build_score_matrix(
    expected_home_goals: float,
    expected_away_goals: float,
    *,
    max_goals: int = 10,
    rho: float = 0.0,
) -> tuple[np.ndarray, float]:
    raw = np.zeros((max_goals + 1, max_goals + 1), dtype=float)
    for home in range(max_goals + 1):
        for away in range(max_goals + 1):
            correction = dixon_coles_tau(home, away, expected_home_goals, expected_away_goals, rho)
            raw[home, away] = max(
                0.0,
                poisson_pmf(home, expected_home_goals)
                * poisson_pmf(away, expected_away_goals)
                * correction,
            )
    captured_mass = float(raw.sum())
    residual_mass = max(0.0, 1.0 - captured_mass)
    if captured_mass:
        raw /= captured_mass
    return raw, residual_mass


def derive_distribution(matrix: np.ndarray) -> dict[str, object]:
    total = float(matrix.sum())
    if not math.isclose(total, 1.0, abs_tol=1e-12):
        matrix = matrix / total
    home_win = float(np.tril(matrix, -1).sum())
    draw = float(np.trace(matrix))
    away_win = float(np.triu(matrix, 1).sum())
    btts = float(matrix[1:, 1:].sum())
    totals: dict[int, float] = {}
    ranked: list[dict[str, object]] = []
    for home in range(matrix.shape[0]):
        for away in range(matrix.shape[1]):
            probability = float(matrix[home, away])
            totals[home + away] = totals.get(home + away, 0.0) + probability
            ranked.append({"scoreline": f"{home}-{away}", "probability": probability})
    ranked.sort(key=lambda row: (-float(row["probability"]), str(row["scoreline"])))
    bucket_01 = sum(value for goals, value in totals.items() if goals <= 1)
    bucket_23 = sum(value for goals, value in totals.items() if 2 <= goals <= 3)
    bucket_4p = sum(value for goals, value in totals.items() if goals >= 4)
    outcomes = {"HOME": home_win, "DRAW": draw, "AWAY": away_win}
    top = max(outcomes, key=outcomes.get)
    result: dict[str, object] = {
        "home_win_probability": home_win,
        "draw_probability": draw,
        "away_win_probability": away_win,
        "top_probability_outcome": top,
        "btts_yes_probability": btts,
        "btts_no_probability": 1.0 - btts,
        "total_goals_0_1_probability": bucket_01,
        "total_goals_2_3_probability": bucket_23,
        "total_goals_4_plus_probability": bucket_4p,
        "top_scoreline": ranked[0]["scoreline"],
        "top_3_scorelines": [row["scoreline"] for row in ranked[:3]],
        "top_5_scorelines": [row["scoreline"] for row in ranked[:5]],
        "ranked_scorelines": ranked,
        "probability_sum": home_win + draw + away_win,
    }
    for line in (1.5, 2.5, 3.5):
        suffix = str(line).replace(".", "_")
        over = sum(value for goals, value in totals.items() if goals > line)
        result[f"over_{suffix}_probability"] = over
        result[f"under_{suffix}_probability"] = 1.0 - over
    return result
