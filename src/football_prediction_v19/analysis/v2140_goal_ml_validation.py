# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import math
from collections import defaultdict

import numpy as np
import pandas as pd

from football_prediction_v19.analysis.v2130_goal_model_evaluation import evaluate_predictions
from football_prediction_v19.analysis.v2130_poisson_models import poisson_deviance
from football_prediction_v19.analysis.v2140_goal_ml_models import (
    ModelConfiguration,
    fit_goal_pair,
    model_configurations,
    predict_goal_pair,
)
from football_prediction_v19.analysis.v2140_goal_probability_outputs import attach_probability_outputs


LEAGUE_BASELINE = "LEAGUE_MEAN_BASELINE"
DC_BASELINE = "V2131_DIXON_COLES"
COMPLEXITY = {
    "REGULARIZED_POISSON_GLM": 0,
    "HIST_GRADIENT_BOOSTING_POISSON": 1,
    "GRADIENT_BOOSTING_REGRESSION": 2,
    "RANDOM_FOREST_COUNT_REGRESSION": 3,
}
KEYS = ["competition", "season", "match_date", "home_team", "away_team"]


def outer_fold_definitions(dataset: pd.DataFrame) -> list[dict[str, object]]:
    definitions = []
    premier = dataset["competition"].eq("Premier League")
    for season in sorted(dataset.loc[premier, "season"].unique()):
        holdout = premier & dataset["season"].eq(season)
        definitions.append({
            "fold_type": "LOSO", "holdout": str(season),
            "train_mask": premier & ~holdout, "holdout_mask": holdout,
        })
    for competition in sorted(dataset["competition"].unique()):
        holdout = dataset["competition"].eq(competition)
        definitions.append({
            "fold_type": "LOCO", "holdout": str(competition),
            "train_mask": ~holdout, "holdout_mask": holdout,
        })
    return definitions


def chronological_inner_split(train: pd.DataFrame, validation_fraction: float = .20) -> tuple[pd.DataFrame, pd.DataFrame]:
    ordered = train.sort_values(["match_date", "competition", "home_team"]).reset_index(drop=True)
    split = max(1, min(len(ordered) - 1, int(len(ordered) * (1 - validation_fraction))))
    cutoff = ordered.iloc[split]["match_date"]
    inner_train = ordered[ordered["match_date"] < cutoff]
    validation = ordered[ordered["match_date"] >= cutoff]
    if inner_train.empty or validation.empty:
        inner_train, validation = ordered.iloc[:split], ordered.iloc[split:]
    return inner_train, validation


def run_nested_validation(
    dataset: pd.DataFrame,
    frozen_dc: pd.DataFrame,
) -> dict[str, object]:
    all_inner = []
    outer_rows = []
    prediction_parts: dict[str, list[pd.DataFrame]] = defaultdict(list)
    training_rows = []
    failures = 0
    for definition in outer_fold_definitions(dataset):
        outer_train = dataset[definition["train_mask"]].copy()
        holdout = dataset[definition["holdout_mask"]].copy()
        inner_train, inner_validation = chronological_inner_split(outer_train)
        config_scores = []
        for config in model_configurations():
            try:
                models = fit_goal_pair(inner_train, config)
                home, away, clipped = predict_goal_pair(models, inner_validation)
                total_actual = inner_validation["actual_home_goals"].to_numpy() + inner_validation["actual_away_goals"].to_numpy()
                total_mae = float(np.mean(np.abs(total_actual - home - away)))
                deviance = float(np.mean([
                    poisson_deviance(ah, ph) + poisson_deviance(aa, pa)
                    for ah, aa, ph, pa in zip(
                        inner_validation["actual_home_goals"], inner_validation["actual_away_goals"], home, away
                    )
                ]))
                score = {
                    "fold_type": definition["fold_type"], "holdout": definition["holdout"],
                    "model_name": config.model_name, "parameters": config.parameter_json,
                    "inner_training_rows": len(inner_train), "inner_validation_rows": len(inner_validation),
                    "validation_start": str(inner_validation["match_date"].min().date()),
                    "validation_end": str(inner_validation["match_date"].max().date()),
                    "inner_total_goals_mae": total_mae, "inner_poisson_deviance": deviance,
                    "inner_clipped_count": int(clipped.sum()), "training_failed": False,
                }
                config_scores.append((config, score))
                all_inner.append(score)
            except Exception as exc:
                failures += 1
                score = {
                    "fold_type": definition["fold_type"], "holdout": definition["holdout"],
                    "model_name": config.model_name, "parameters": config.parameter_json,
                    "inner_training_rows": len(inner_train), "inner_validation_rows": len(inner_validation),
                    "validation_start": "", "validation_end": "",
                    "inner_total_goals_mae": math.inf, "inner_poisson_deviance": math.inf,
                    "inner_clipped_count": 0, "training_failed": True, "failure": str(exc),
                }
                all_inner.append(score)
        selected_by_class = {}
        for model_name in COMPLEXITY:
            candidates = [(config, score) for config, score in config_scores if config.model_name == model_name]
            selected_by_class[model_name] = _choose_config(candidates)
        for model_name, (config, selection_score) in selected_by_class.items():
            try:
                models = fit_goal_pair(outer_train, config)
                home, away, clipped = predict_goal_pair(models, holdout)
                predictions = attach_probability_outputs(
                    holdout, home, away, model_name=model_name,
                    model_parameters=config.parameter_json, clipped=clipped,
                )
                predictions["fold_type"] = definition["fold_type"]
                predictions["outer_holdout"] = definition["holdout"]
                prediction_parts[model_name].append(predictions)
                metric = evaluate_predictions(predictions, model_name)
                outer_rows.append(_outer_record(definition, outer_train, holdout, config, selection_score, metric))
                training_rows.append({
                    "fold_type": definition["fold_type"], "holdout": definition["holdout"],
                    "model_name": model_name, "parameters": config.parameter_json,
                    "training_row_count": len(outer_train), "training_failed": False,
                })
            except Exception as exc:
                failures += 1
                training_rows.append({
                    "fold_type": definition["fold_type"], "holdout": definition["holdout"],
                    "model_name": model_name, "parameters": config.parameter_json,
                    "training_row_count": len(outer_train), "training_failed": True, "failure": str(exc),
                })
        baseline_predictions = attach_probability_outputs(
            holdout,
            holdout["league_home_goals_mean"].to_numpy(),
            holdout["league_away_goals_mean"].to_numpy(),
            model_name=LEAGUE_BASELINE, model_parameters="{}",
        )
        baseline_predictions["fold_type"] = definition["fold_type"]
        baseline_predictions["outer_holdout"] = definition["holdout"]
        prediction_parts[LEAGUE_BASELINE].append(baseline_predictions)
        outer_rows.append(_outer_record(
            definition, outer_train, holdout,
            ModelConfiguration(LEAGUE_BASELINE, {}), {"inner_total_goals_mae": None},
            evaluate_predictions(baseline_predictions, LEAGUE_BASELINE),
        ))
        dc_predictions = _frozen_dc_for_holdout(holdout, frozen_dc)
        dc_predictions["fold_type"] = definition["fold_type"]
        dc_predictions["outer_holdout"] = definition["holdout"]
        prediction_parts[DC_BASELINE].append(dc_predictions)
        outer_rows.append(_outer_record(
            definition, outer_train, holdout,
            ModelConfiguration(DC_BASELINE, {"rho": -0.1, "shrinkage_weight": 10}),
            {"inner_total_goals_mae": None},
            evaluate_predictions(dc_predictions, DC_BASELINE),
        ))
    return {
        "inner_selection_summary": pd.DataFrame(all_inner),
        "outer_holdout_summary": pd.DataFrame(outer_rows),
        "model_training_summary": pd.DataFrame(training_rows),
        "predictions_by_model": {
            model: pd.concat(parts, ignore_index=True) for model, parts in prediction_parts.items()
        },
        "training_failure_count": failures,
    }


def aggregate_model_comparison(validation: dict[str, object]) -> pd.DataFrame:
    predictions_by_model = validation["predictions_by_model"]
    outer = validation["outer_holdout_summary"]
    rows = []
    for model, predictions in predictions_by_model.items():
        loco = predictions[predictions["fold_type"].eq("LOCO")]
        metrics = evaluate_predictions(loco, model)
        model_outer = outer[outer["model_name"].eq(model)].copy()
        baseline_outer = outer[outer["model_name"].eq(LEAGUE_BASELINE)][
            ["fold_type", "holdout", "total_goals_mae", "btts_brier_score", "over_2_5_brier_score", "multiclass_brier_score"]
        ].rename(columns={column: f"baseline_{column}" for column in (
            "total_goals_mae", "btts_brier_score", "over_2_5_brier_score", "multiclass_brier_score"
        )})
        merged = model_outer.merge(baseline_outer, on=["fold_type", "holdout"], how="left")
        changes = merged["baseline_total_goals_mae"] - merged["total_goals_mae"]
        metrics.update({
            "outer_holdout_count": len(model_outer),
            "positive_total_goals_holdout_count": int(changes.gt(0).sum()),
            "positive_total_goals_holdout_rate": float(changes.gt(0).mean()),
            "positive_btts_holdout_count": int((merged["baseline_btts_brier_score"] > merged["btts_brier_score"]).sum()),
            "positive_over_2_5_holdout_count": int((merged["baseline_over_2_5_brier_score"] > merged["over_2_5_brier_score"]).sum()),
            "positive_winner_brier_holdout_count": int((merged["baseline_multiclass_brier_score"] > merged["multiclass_brier_score"]).sum()),
            "mean_holdout_mae_improvement": float(changes.mean()),
            "median_holdout_mae_improvement": float(changes.median()),
            "worst_holdout_mae_change": float(changes.min()),
        })
        rows.append(metrics)
    return pd.DataFrame(rows)


def _choose_config(candidates):
    best_mae = min(score["inner_total_goals_mae"] for _, score in candidates)
    eligible = [(config, score) for config, score in candidates if score["inner_total_goals_mae"] <= best_mae * 1.005]
    return min(eligible, key=lambda item: (
        item[1]["inner_poisson_deviance"],
        len(item[0].parameters),
        item[0].parameter_json,
    ))


def _outer_record(definition, train, holdout, config, selection_score, metrics):
    return {
        "fold_type": definition["fold_type"], "holdout": definition["holdout"],
        "training_competitions": json.dumps(sorted(train["competition"].unique().tolist())),
        "training_seasons": json.dumps(sorted(train["season"].unique().tolist())),
        "validation_period": f"{train['match_date'].min().date()}..{train['match_date'].max().date()}",
        "selected_model": config.model_name, "model_name": config.model_name,
        "selected_parameters": config.parameter_json, "selection_source": "INNER_TRAINING_ONLY",
        "holdout_used_for_selection": False, "training_row_count": len(train), "holdout_row_count": len(holdout),
        "inner_validation_total_goals_mae": selection_score.get("inner_total_goals_mae"),
        **{key: value for key, value in metrics.items() if key not in ("model_name", "rows_evaluated")},
    }


def _frozen_dc_for_holdout(holdout: pd.DataFrame, frozen: pd.DataFrame) -> pd.DataFrame:
    columns = KEYS + ["expected_home_goals", "expected_away_goals"]
    source = frozen.copy()
    source["match_date"] = pd.to_datetime(source["match_date"])
    merged = holdout.merge(source[columns], on=KEYS, how="left")
    return attach_probability_outputs(
        merged,
        merged["expected_home_goals"].to_numpy(),
        merged["expected_away_goals"].to_numpy(),
        model_name=DC_BASELINE,
        model_parameters=json.dumps({"rho": -0.1, "shrinkage_weight": 10}),
        rho=-0.1,
    )
