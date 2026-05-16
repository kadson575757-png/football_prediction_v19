from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer, make_column_selector
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .data import feature_columns, load_matches
from .features import build_features, build_fixture_features

TARGET = "result"
CLASS_ORDER = ["H", "D", "A"]


def _one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:  # older sklearn
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def build_pipeline(model_name: str = "random_forest", random_state: int = 42) -> Pipeline:
    numeric_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    categorical_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", _one_hot_encoder()),
    ])
    preprocessor = ColumnTransformer([
        ("num", numeric_pipe, make_column_selector(dtype_include=np.number)),
        ("cat", categorical_pipe, make_column_selector(dtype_exclude=np.number)),
    ], remainder="drop")

    if model_name == "logistic_regression":
        try:
            clf = LogisticRegression(max_iter=2000, multi_class="auto", random_state=random_state)
        except TypeError:
            clf = LogisticRegression(max_iter=2000, random_state=random_state)
    elif model_name == "gradient_boosting":
        clf = GradientBoostingClassifier(random_state=random_state)
    else:
        clf = RandomForestClassifier(
            n_estimators=300,
            max_depth=8,
            min_samples_leaf=3,
            class_weight="balanced_subsample",
            random_state=random_state,
        )
    return Pipeline([("preprocess", preprocessor), ("classifier", clf)])


def _brier_multiclass(y_true: pd.Series, proba: np.ndarray, classes: list[str]) -> float:
    one_hot = np.zeros_like(proba, dtype=float)
    idx = {c: i for i, c in enumerate(classes)}
    for r, label in enumerate(y_true):
        if label in idx:
            one_hot[r, idx[label]] = 1.0
    return float(np.mean(np.sum((proba - one_hot) ** 2, axis=1)))


def _log_loss_multiclass(y_true: pd.Series, proba: np.ndarray, classes: list[str]) -> float:
    eps = 1e-15
    proba = np.clip(proba, eps, 1.0 - eps)
    proba = proba / proba.sum(axis=1, keepdims=True)
    idx = {c: i for i, c in enumerate(classes)}
    losses = []
    for r, label in enumerate(y_true):
        if label in idx:
            losses.append(-np.log(proba[r, idx[label]]))
    return float(np.mean(losses)) if losses else float("nan")


def _align_proba(model: Any, proba: np.ndarray) -> pd.DataFrame:
    try:
        classes = list(model.named_steps["classifier"].classes_)
    except (AttributeError, KeyError):
        # CalibratedClassifierCV or other wrapper exposes classes_ directly
        classes = list(model.classes_)
    out = pd.DataFrame(proba, columns=classes)
    for c in CLASS_ORDER:
        if c not in out.columns:
            out[c] = 0.0
    return out[CLASS_ORDER]


def train_from_feature_table(
    table: pd.DataFrame,
    model_name: str = "random_forest",
    test_season: int | None = None,
    tune: bool = False,
    random_state: int = 42,
) -> tuple[Pipeline, dict[str, Any], list[str]]:
    table = table.dropna(subset=[TARGET]).copy()
    cols = [c for c in feature_columns(table) if not table[c].isna().all()]

    if test_season is None:
        train = table
        test = table.iloc[0:0].copy()
    else:
        train = table[table["season_start"] < test_season]
        test = table[table["season_start"] == test_season]
        if train.empty or test.empty:
            train = table[table["season_start"] <= test_season]
            test = table[table["season_start"] > test_season]

    X_train = train[cols]
    y_train = train[TARGET]
    model = build_pipeline(model_name=model_name, random_state=random_state)

    if tune and model_name == "random_forest":
        param_grid = {
            "classifier__n_estimators": [100, 300, 500],
            "classifier__max_depth": [4, 8, 12, None],
            "classifier__min_samples_leaf": [1, 3, 6],
        }
        model = GridSearchCV(model, param_grid=param_grid, cv=3, scoring="neg_log_loss", n_jobs=-1)
        model.fit(X_train, y_train)
        best = model.best_estimator_
        best_params = model.best_params_
    else:
        model.fit(X_train, y_train)
        best = model
        best_params = {}

    metrics: dict[str, Any] = {
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "feature_count": int(len(cols)),
        "classes": list(best.named_steps["classifier"].classes_),
        "best_params": best_params,
    }

    if len(test) > 0:
        X_test = test[cols]
        y_test = test[TARGET]
        pred = best.predict(X_test)
        proba = _align_proba(best, best.predict_proba(X_test))
        metrics["accuracy"] = float(accuracy_score(y_test, pred))
        metrics["log_loss"] = _log_loss_multiclass(y_test, proba[CLASS_ORDER].to_numpy(), CLASS_ORDER)
        metrics["brier_multiclass"] = _brier_multiclass(y_test, proba[CLASS_ORDER].to_numpy(), CLASS_ORDER)
        metrics["confusion_matrix"] = confusion_matrix(y_test, pred, labels=CLASS_ORDER).tolist()
        metrics["confusion_matrix_labels"] = CLASS_ORDER
    return best, metrics, cols


def train_from_matches(
    matches: pd.DataFrame,
    model_name: str = "random_forest",
    test_season: int | None = None,
    min_history: int = 1,
    tune: bool = False,
    random_state: int = 42,
) -> tuple[Pipeline, pd.DataFrame, dict[str, Any], list[str]]:
    table = build_features(matches, min_history=min_history)
    model, metrics, cols = train_from_feature_table(table, model_name, test_season, tune, random_state)
    return model, table, metrics, cols


def save_model(path: str | Path, model: Pipeline, feature_cols: list[str], metrics: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_cols": feature_cols, "metrics": metrics}, path)


def load_model(path: str | Path) -> dict[str, Any]:
    return joblib.load(path)


def predict_feature_rows(model_bundle: dict[str, Any], feature_rows: pd.DataFrame) -> pd.DataFrame:
    model: Pipeline = model_bundle["model"]
    cols = model_bundle["feature_cols"]
    X = feature_rows.reindex(columns=cols)
    proba = _align_proba(model, model.predict_proba(X))
    pred = model.predict(X)
    out = feature_rows.copy()
    out["predicted_result"] = pred
    out["prob_home"] = proba["H"].to_numpy()
    out["prob_draw"] = proba["D"].to_numpy()
    out["prob_away"] = proba["A"].to_numpy()
    return out


def train_save(input_path: str | Path, model_path: str | Path, test_season: int | None = None, tune: bool = False) -> dict[str, Any]:
    matches = load_matches(input_path)
    model, table, metrics, cols = train_from_matches(matches, test_season=test_season, tune=tune)
    save_model(model_path, model, cols, metrics)
    return metrics
