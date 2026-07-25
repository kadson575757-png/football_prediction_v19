from pathlib import Path

import numpy as np
import pandas as pd

from football_prediction_v19.analysis.v2140_goal_ml_dataset import (
    TARGET_COLUMNS, build_goal_ml_dataset, feature_columns, load_existing_probability_context,
)
from football_prediction_v19.analysis.v2140_goal_ml_models import (
    ModelConfiguration, fit_goal_pair, predict_goal_pair,
)
from football_prediction_v19.analysis.v2140_goal_ml_validation import (
    chronological_inner_split, outer_fold_definitions, run_nested_validation,
)
from football_prediction_v19.analysis.v2140_goal_probability_outputs import attach_probability_outputs
from scripts.run_v2140_alternative_goal_model_benchmark import (
    SAFETY, _dominance, _existing_winner_metrics, run_v2140_alternative_goal_model_benchmark,
)


def _matches(rounds=12, competitions=("Premier League",), seasons=("2023/24",)):
    rows, date = [], pd.Timestamp("2023-08-01")
    for competition in competitions:
        for season in seasons:
            for index in range(rounds):
                rows.append({
                    "match_date": date, "competition": competition, "season": season,
                    "home_team": "Alpha" if index % 2 == 0 else "Beta",
                    "away_team": "Beta" if index % 2 == 0 else "Alpha",
                    "actual_home_goals": index % 4, "actual_away_goals": (index + 1) % 3,
                })
                date += pd.Timedelta(days=1)
    return pd.DataFrame(rows)


def _dataset(**kwargs):
    matches = _matches(**kwargs)
    context = matches[["competition", "season", "match_date", "home_team", "away_team"]].copy()
    context["base_home_probability"] = .42
    context["base_draw_probability"] = .29
    context["base_away_probability"] = .29
    context["base_probability_edge"] = .13
    return build_goal_ml_dataset(matches, probability_context=context)


def _frozen_dc(data):
    result = data[["competition", "season", "match_date", "home_team", "away_team"]].copy()
    result["expected_home_goals"] = data["league_home_goals_mean"].to_numpy()
    result["expected_away_goals"] = data["league_away_goals_mean"].to_numpy()
    return result


def test_rolling_dataset_is_chronological_and_excludes_targets_from_features():
    data = _dataset(rounds=8)
    numeric, categorical = feature_columns()
    assert data["match_date"].is_monotonic_increasing
    assert not set(TARGET_COLUMNS) & set(numeric + categorical)
    assert data["post_match_rows_used_count"].sum() == 0
    assert data["asof_clean"].all()
    assert data.iloc[0]["home_prior_matches_count"] == 0


def test_missing_indicators_exist_without_full_dataset_imputation():
    data = build_goal_ml_dataset(_matches(rounds=4), probability_context=pd.DataFrame())
    assert data["base_home_probability"].isna().all()
    assert data["base_home_probability_missing"].eq(1).all()


def test_project_probability_context_includes_premier_league():
    context = load_existing_probability_context(".")
    assert context["competition"].eq("Premier League").sum() == 1140
    assert context[["base_home_probability", "base_draw_probability", "base_away_probability"]].notna().all().all()


def test_training_only_preprocessing_and_poisson_glm_predictions():
    data = _dataset(rounds=12)
    train, holdout = data.iloc[:8], data.iloc[8:]
    config = ModelConfiguration("REGULARIZED_POISSON_GLM", {"alpha": .1})
    models = fit_goal_pair(train, config)
    home, away, clipped = predict_goal_pair(models, holdout)
    assert len(home) == len(holdout)
    assert np.isfinite(home).all() and np.isfinite(away).all()
    assert ((home >= .1) & (home <= 5)).all()
    assert clipped.dtype == bool


def test_hist_gradient_boosting_prediction_validity_and_clipping():
    data = _dataset(rounds=24)
    config = ModelConfiguration("HIST_GRADIENT_BOOSTING_POISSON", {
        "learning_rate": .05, "max_leaf_nodes": 7, "min_samples_leaf": 20, "l2_regularization": .1,
    })
    models = fit_goal_pair(data.iloc[:18], config)
    home, away, clipped = predict_goal_pair(models, data.iloc[18:])
    outputs = attach_probability_outputs(
        data.iloc[18:], home, away, model_name=config.model_name,
        model_parameters=config.parameter_json, clipped=clipped,
    )
    assert not outputs["invalid_prediction"].any()
    assert outputs["probability_sum"].sub(1).abs().max() <= 1e-12
    assert outputs["score_matrix_residual_mass"].max() < 1e-8
    assert outputs["top_3_scorelines"].map(len).eq(3).all()


def test_explicit_lambda_clipping():
    data = _dataset(rounds=2)
    outputs = attach_probability_outputs(
        data, [20, -2], [30, -1], model_name="TEST", model_parameters="{}",
        clipped=[True, True],
    )
    assert outputs["lambda_clipped"].all()
    assert outputs["expected_home_goals"].between(.1, 5).all()
    assert outputs["expected_away_goals"].between(.1, 5).all()


def test_inner_and_outer_splits_are_separate_and_chronological():
    data = _dataset(
        rounds=4, competitions=("Premier League", "La Liga", "Bundesliga"),
        seasons=("2023/24", "2024/25"),
    )
    train, validation = chronological_inner_split(data)
    assert train["match_date"].max() < validation["match_date"].min()
    folds = outer_fold_definitions(data)
    assert {fold["fold_type"] for fold in folds} == {"LOSO", "LOCO"}
    for fold in folds:
        assert not (fold["train_mask"] & fold["holdout_mask"]).any()


def test_nested_validation_records_no_holdout_parameter_selection(monkeypatch):
    data = _dataset(
        rounds=4, competitions=("Premier League", "La Liga"),
        seasons=("2023/24", "2024/25"),
    )
    import football_prediction_v19.analysis.v2140_goal_ml_validation as validation_module
    monkeypatch.setattr(validation_module, "model_configurations", lambda: [
        ModelConfiguration("REGULARIZED_POISSON_GLM", {"alpha": .1}),
        ModelConfiguration("HIST_GRADIENT_BOOSTING_POISSON", {
            "learning_rate": .05, "max_leaf_nodes": 7, "min_samples_leaf": 20, "l2_regularization": .1,
        }),
        ModelConfiguration("GRADIENT_BOOSTING_REGRESSION", {"learning_rate": .05, "max_depth": 2}),
        ModelConfiguration("RANDOM_FOREST_COUNT_REGRESSION", {"n_estimators": 10, "min_samples_leaf": 2}),
    ])
    result = run_nested_validation(data, _frozen_dc(data))
    outer = result["outer_holdout_summary"]
    assert outer["selection_source"].eq("INNER_TRAINING_ONLY").all()
    assert not outer["holdout_used_for_selection"].any()
    assert result["inner_selection_summary"]["inner_validation_rows"].gt(0).all()


def test_dominance_audit_is_bounded():
    data = _dataset(rounds=4)
    baseline = attach_probability_outputs(
        data, [1.4] * len(data), [1.1] * len(data), model_name="BASE", model_parameters="{}",
    )
    best = attach_probability_outputs(
        data, [1.5] * len(data), [1.2] * len(data), model_name="BEST", model_parameters="{}",
    )
    result = _dominance(best, baseline)
    assert 0 <= result["dominant_competition_share"] <= 1
    assert 0 <= result["dominant_team_share"] <= 1


def test_existing_winner_comparison_metrics():
    metrics = _existing_winner_metrics(_dataset(rounds=6))
    assert 0 <= metrics["top_outcome_hit_rate"] <= 1
    assert metrics["multiclass_brier_score"] >= 0


def test_script_core_files_and_safety_flags_exist():
    for path in (
        "scripts/run_v2140_alternative_goal_model_benchmark.py",
        "src/football_prediction_v19/analysis/v2140_goal_ml_dataset.py",
        "src/football_prediction_v19/analysis/v2140_goal_ml_models.py",
        "src/football_prediction_v19/analysis/v2140_goal_ml_validation.py",
        "src/football_prediction_v19/analysis/v2140_goal_probability_outputs.py",
    ):
        assert Path(path).exists()
    assert SAFETY == {
        "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False,
    }
