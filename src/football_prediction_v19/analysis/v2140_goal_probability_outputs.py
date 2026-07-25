# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v2130_match_profile import derive_match_profile
from football_prediction_v19.analysis.v2130_score_matrix import build_score_matrix, derive_distribution


def attach_probability_outputs(
    rows: pd.DataFrame,
    lambda_home,
    lambda_away,
    *,
    model_name: str,
    model_parameters: str,
    clipped=None,
    rho: float = 0.0,
) -> pd.DataFrame:
    records = []
    clipped_values = list(clipped) if clipped is not None else [False] * len(rows)
    for position, (_, row) in enumerate(rows.reset_index(drop=True).iterrows()):
        raw_home = float(lambda_home[position])
        raw_away = float(lambda_away[position])
        home = max(.10, min(raw_home, 5.00))
        away = max(.10, min(raw_away, 5.00))
        was_clipped = bool(clipped_values[position]) or home != raw_home or away != raw_away
        max_goals = 8
        matrix, residual = build_score_matrix(home, away, max_goals=max_goals, rho=rho)
        while residual >= 1e-8 and max_goals < 26:
            max_goals += 2
            matrix, residual = build_score_matrix(home, away, max_goals=max_goals, rho=rho)
        distribution = derive_distribution(matrix)
        record = row.to_dict()
        record.update(distribution)
        invalid = not (
            .10 <= home <= 5.0 and .10 <= away <= 5.0
            and abs(float(distribution["probability_sum"]) - 1.0) <= 1e-12
            and residual < 1e-8
        )
        record.update({
            "model_name": model_name,
            "model_parameters": model_parameters,
            "expected_home_goals": home,
            "expected_away_goals": away,
            "expected_total_goals": home + away,
            "lambda_clipped": was_clipped,
            "invalid_prediction": invalid,
            "probability_valid": not invalid,
            "matrix_max_goals": max_goals,
            "score_matrix_residual_mass": residual,
            "match_profile": derive_match_profile(distribution, home, away),
        })
        records.append(record)
    return pd.DataFrame(records)
