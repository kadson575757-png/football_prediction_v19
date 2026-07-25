"""Two-stage draw/non-draw and home/away winner model."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


FEATURE_GROUPS = {
    "A": ["base_home_probability", "base_draw_probability", "base_away_probability", "base_probability_edge"],
    "B": ["goal_home_probability", "goal_draw_probability", "goal_away_probability", "expected_home_goals", "expected_away_goals"],
    "C": ["rating_difference", "rating_uncertainty", "rating_momentum_last5", "rating_momentum_last10"],
    "D": ["home_last5_points", "away_last5_points", "home_venue_points_per_match", "away_venue_points_per_match"],
    "E": ["rolling_league_draw_rate", "home_team_draw_rate", "away_team_draw_rate", "low_score_probability"],
    "F": ["model_agreement", "maximum_model_probability_difference"],
    "G": ["season_phase", "history_quality_numeric", "fallback_applied"],
}
ABLATIONS = ("A", "A+B", "A+C", "A+B+C", "A+B+C+D", "A+B+C+D+E", "A+B+C+D+E+F+G")


def columns_for_groups(groups: str) -> list[str]:
    return [column for group in groups.split("+") for column in FEATURE_GROUPS[group]]


def fit_hierarchical_model(train: pd.DataFrame, feature_groups: str = "A+B+C+D+E+F+G", c: float = 1.0) -> dict:
    columns = columns_for_groups(feature_groups)
    draw_target = train["actual_result"].eq("DRAW").astype(int)
    non_draw = train[~train["actual_result"].eq("DRAW")]
    home_target = non_draw["actual_result"].eq("HOME").astype(int)
    return {
        "draw_model": _fit_binary(train[columns], draw_target, c),
        "home_away_model": _fit_binary(non_draw[columns], home_target, c),
        "columns": columns,
        "feature_groups": feature_groups,
        "c": c,
    }


def predict_hierarchical(model: dict, rows: pd.DataFrame) -> np.ndarray:
    x = rows[model["columns"]]
    draw = _positive_probability(model["draw_model"], x)
    home_given = _positive_probability(model["home_away_model"], x)
    return reconstruct_probabilities(draw, home_given)


def reconstruct_probabilities(draw_probability, home_given_non_draw) -> np.ndarray:
    draw = np.clip(np.asarray(draw_probability, dtype=float), 1e-9, 1 - 1e-9)
    home_given = np.clip(np.asarray(home_given_non_draw, dtype=float), 1e-9, 1 - 1e-9)
    result = np.column_stack(((1.0 - draw) * home_given, draw, (1.0 - draw) * (1.0 - home_given)))
    return result / result.sum(axis=1, keepdims=True)


def _fit_binary(x: pd.DataFrame, y: pd.Series, c: float):
    if y.nunique() < 2:
        return {"constant": float(y.iloc[0]) if len(y) else 0.5}
    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("model", LogisticRegression(C=c, max_iter=1000, class_weight="balanced")),
    ])
    pipeline.fit(x, y)
    return pipeline


def _positive_probability(model, x: pd.DataFrame) -> np.ndarray:
    if isinstance(model, dict):
        return np.full(len(x), model["constant"])
    return model.predict_proba(x)[:, 1]
