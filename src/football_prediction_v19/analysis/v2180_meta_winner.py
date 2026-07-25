"""Small controlled meta-winner candidates trained on OOF base outputs."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


META_CONTEXT = [
    "rating_difference", "expected_home_goals", "expected_away_goals",
    "model_agreement", "maximum_model_probability_difference",
    "base_probability_edge", "season_phase", "history_quality_numeric",
]


def meta_features(rows: pd.DataFrame, hierarchical_probabilities: np.ndarray) -> pd.DataFrame:
    result = pd.DataFrame(index=rows.index)
    for prefix, columns in (
        ("primary", ["base_home_probability", "base_draw_probability", "base_away_probability"]),
        ("goal", ["goal_home_probability", "goal_draw_probability", "goal_away_probability"]),
        ("rating", ["rating_home_probability", "rating_draw_probability", "rating_away_probability"]),
    ):
        for outcome, column in zip(("home", "draw", "away"), columns):
            result[f"{prefix}_{outcome}"] = rows[column].to_numpy()
    for index, outcome in enumerate(("home", "draw", "away")):
        result[f"hierarchical_{outcome}"] = hierarchical_probabilities[:, index]
    for column in META_CONTEXT:
        result[column] = rows[column].to_numpy()
    return result


def fit_meta_model(x: pd.DataFrame, y: pd.Series, model_name: str, params: dict) -> object:
    target = pd.Categorical(y, categories=["HOME", "DRAW", "AWAY"]).codes
    if model_name == "MULTINOMIAL_LOGISTIC_STACKER":
        model = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("model", LogisticRegression(C=float(params["C"]), max_iter=1000)),
        ])
    elif model_name == "HIST_GRADIENT_BOOSTING_STACKER":
        model = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", HistGradientBoostingClassifier(
                learning_rate=float(params["learning_rate"]),
                max_leaf_nodes=int(params["max_leaf_nodes"]),
                min_samples_leaf=int(params["min_samples_leaf"]),
                l2_regularization=float(params["l2_regularization"]),
                max_iter=100,
                random_state=2180,
            )),
        ])
    else:
        raise ValueError(f"Unknown meta model: {model_name}")
    model.fit(x, target)
    return model


def predict_meta_model(model, x: pd.DataFrame) -> np.ndarray:
    probabilities = model.predict_proba(x)
    return probabilities / probabilities.sum(axis=1, keepdims=True)


def meta_candidates() -> list[tuple[str, dict]]:
    logistic = [("MULTINOMIAL_LOGISTIC_STACKER", {"C": value}) for value in (0.1, 1.0, 10.0)]
    hist = [
        ("HIST_GRADIENT_BOOSTING_STACKER", {
            "learning_rate": rate, "max_leaf_nodes": leaves,
            "min_samples_leaf": minimum, "l2_regularization": regularization,
        })
        for rate in (0.03, 0.05)
        for leaves in (7, 15)
        for minimum in (30, 60)
        for regularization in (0.1, 1.0)
    ]
    return logistic + hist
