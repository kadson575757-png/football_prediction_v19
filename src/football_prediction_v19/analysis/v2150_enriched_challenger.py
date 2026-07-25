# -*- coding: utf-8 -*-
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import TweedieRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from football_prediction_v19.analysis.v2140_goal_ml_dataset import NUMERIC_COLUMNS
from football_prediction_v19.analysis.v2150_feature_coverage import GROUP_FEATURES


BASE_MODEL = "MODEL_0_V2131_DIXON_COLES"


def ablation_definitions(passing_groups: list[str]) -> list[dict[str, object]]:
    definitions = [{"model_name": BASE_MODEL, "feature_groups": [], "model_class": "FROZEN_BASELINE"}]
    stages = [
        ("MODEL_1_XG", ["EXPECTED_GOALS"]),
        ("MODEL_2_XG_CHANCE", ["EXPECTED_GOALS", "CHANCE_CREATION"]),
        ("MODEL_3_XG_SQUAD", ["EXPECTED_GOALS", "SQUAD_AVAILABILITY"]),
        ("MODEL_4_XG_MARKET", ["EXPECTED_GOALS", "MARKET_CONTEXT"]),
    ]
    for name, groups in stages:
        if all(group in passing_groups for group in groups):
            definitions.append({"model_name": name, "feature_groups": groups, "model_class": "GRADIENT_BOOSTING"})
    if passing_groups:
        definitions.append({
            "model_name": "MODEL_5_ALL_PASSING", "feature_groups": sorted(passing_groups),
            "model_class": "GRADIENT_BOOSTING",
        })
        definitions.append({
            "model_name": "MODEL_5_ALL_PASSING_GLM_CONTROL", "feature_groups": sorted(passing_groups),
            "model_class": "REGULARIZED_GLM",
        })
    # If xG fails but another group passes, preserve a transparent isolated ablation.
    for group in passing_groups:
        if not any(definition["feature_groups"] == [group] for definition in definitions):
            definitions.append({
                "model_name": f"ISOLATED_{group}", "feature_groups": [group],
                "model_class": "GRADIENT_BOOSTING",
            })
    return definitions


def model_feature_columns(feature_groups: list[str]) -> list[str]:
    columns = list(NUMERIC_COLUMNS)
    for group in feature_groups:
        columns.extend(GROUP_FEATURES[group])
        columns.extend(f"{feature}_missing_indicator" for feature in GROUP_FEATURES[group])
    return list(dict.fromkeys(columns))


def fit_enriched_pair(train: pd.DataFrame, definition: dict[str, object]) -> tuple[Pipeline, Pipeline]:
    columns = model_feature_columns(list(definition["feature_groups"]))
    model_class = str(definition["model_class"])
    home = _pipeline(columns, model_class)
    away = _pipeline(columns, model_class)
    home.fit(train[columns + ["competition"]], train["actual_home_goals"].astype(float))
    away.fit(train[columns + ["competition"]], train["actual_away_goals"].astype(float))
    return home, away


def predict_enriched_pair(models, rows, feature_groups):
    columns = model_feature_columns(list(feature_groups))
    matrix = rows[columns + ["competition"]]
    raw_home = np.asarray(models[0].predict(matrix), float)
    raw_away = np.asarray(models[1].predict(matrix), float)
    home, away = np.clip(raw_home, .10, 5.0), np.clip(raw_away, .10, 5.0)
    return home, away, (home != raw_home) | (away != raw_away)


def _pipeline(columns: list[str], model_class: str) -> Pipeline:
    numeric_steps = [("imputer", SimpleImputer(strategy="median"))]
    if model_class == "REGULARIZED_GLM":
        numeric_steps.append(("scaler", StandardScaler()))
        estimator = TweedieRegressor(power=1, alpha=.1, link="log", max_iter=1000)
    else:
        estimator = GradientBoostingRegressor(
            loss="huber", n_estimators=150, learning_rate=.03, max_depth=2,
            min_samples_leaf=20, random_state=2150,
        )
    preprocess = ColumnTransformer([
        ("numeric", Pipeline(numeric_steps), columns),
        ("competition", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["competition"]),
    ], sparse_threshold=0.0)
    return Pipeline([("preprocess", preprocess), ("model", estimator)])
