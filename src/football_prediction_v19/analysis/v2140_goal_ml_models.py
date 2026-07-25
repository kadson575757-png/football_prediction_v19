# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import TweedieRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from football_prediction_v19.analysis.v2140_goal_ml_dataset import feature_columns


@dataclass(frozen=True)
class ModelConfiguration:
    model_name: str
    parameters: dict[str, object]

    @property
    def parameter_json(self) -> str:
        return json.dumps(self.parameters, sort_keys=True)


def model_configurations() -> list[ModelConfiguration]:
    configs = [
        ModelConfiguration("REGULARIZED_POISSON_GLM", {"alpha": alpha})
        for alpha in (0.01, 0.1, 1.0)
    ]
    configs.extend(
        ModelConfiguration("HIST_GRADIENT_BOOSTING_POISSON", {
            "learning_rate": rate, "max_leaf_nodes": leaves,
            "min_samples_leaf": minimum, "l2_regularization": regularization,
        })
        for rate in (0.03, 0.05)
        for leaves in (7, 15)
        for minimum in (20, 40)
        for regularization in (0.1, 1.0)
    )
    configs.extend([
        ModelConfiguration("GRADIENT_BOOSTING_REGRESSION", {"learning_rate": 0.03, "max_depth": 2}),
        ModelConfiguration("GRADIENT_BOOSTING_REGRESSION", {"learning_rate": 0.05, "max_depth": 2}),
        ModelConfiguration("RANDOM_FOREST_COUNT_REGRESSION", {"n_estimators": 200, "min_samples_leaf": 20}),
    ])
    return configs


def build_model_pipeline(config: ModelConfiguration) -> Pipeline:
    numeric, categorical = feature_columns()
    scale = config.model_name == "REGULARIZED_POISSON_GLM"
    numeric_steps = [("imputer", SimpleImputer(strategy="median", add_indicator=False))]
    if scale:
        numeric_steps.append(("scaler", StandardScaler()))
    preprocessor = ColumnTransformer([
        ("numeric", Pipeline(numeric_steps), numeric),
        ("competition", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]), categorical),
    ], sparse_threshold=0.0)
    parameters = config.parameters
    if config.model_name == "REGULARIZED_POISSON_GLM":
        estimator = TweedieRegressor(
            power=1, alpha=float(parameters["alpha"]), link="log", max_iter=1000, tol=1e-7,
        )
    elif config.model_name == "HIST_GRADIENT_BOOSTING_POISSON":
        estimator = HistGradientBoostingRegressor(
            loss="poisson", learning_rate=float(parameters["learning_rate"]),
            max_leaf_nodes=int(parameters["max_leaf_nodes"]),
            min_samples_leaf=int(parameters["min_samples_leaf"]),
            l2_regularization=float(parameters["l2_regularization"]),
            max_iter=150, early_stopping=False, random_state=2140,
        )
    elif config.model_name == "GRADIENT_BOOSTING_REGRESSION":
        estimator = GradientBoostingRegressor(
            loss="huber", n_estimators=150, learning_rate=float(parameters["learning_rate"]),
            max_depth=int(parameters["max_depth"]), min_samples_leaf=20, random_state=2140,
        )
    elif config.model_name == "RANDOM_FOREST_COUNT_REGRESSION":
        estimator = RandomForestRegressor(
            n_estimators=int(parameters["n_estimators"]),
            min_samples_leaf=int(parameters["min_samples_leaf"]),
            max_features=0.7, n_jobs=-1, random_state=2140,
        )
    else:
        raise ValueError(f"Unknown model: {config.model_name}")
    return Pipeline([("preprocess", preprocessor), ("model", estimator)])


def fit_goal_pair(
    train: pd.DataFrame,
    config: ModelConfiguration,
) -> tuple[Pipeline, Pipeline]:
    numeric, categorical = feature_columns()
    columns = numeric + categorical
    home = build_model_pipeline(config)
    away = build_model_pipeline(config)
    home.fit(train[columns], train["actual_home_goals"].astype(float))
    away.fit(train[columns], train["actual_away_goals"].astype(float))
    return home, away


def predict_goal_pair(
    models: tuple[Pipeline, Pipeline],
    rows: pd.DataFrame,
    *,
    minimum: float = .10,
    maximum: float = 5.00,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    numeric, categorical = feature_columns()
    columns = numeric + categorical
    raw_home = np.asarray(models[0].predict(rows[columns]), dtype=float)
    raw_away = np.asarray(models[1].predict(rows[columns]), dtype=float)
    home = np.clip(raw_home, minimum, maximum)
    away = np.clip(raw_away, minimum, maximum)
    clipped = (home != raw_home) | (away != raw_away)
    return home, away, clipped
