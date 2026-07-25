# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from collections import defaultdict

import numpy as np
import pandas as pd

from football_prediction_v19.analysis.v2130_goal_model_evaluation import evaluate_predictions
from football_prediction_v19.analysis.v2140_goal_ml_validation import KEYS, _frozen_dc_for_holdout, outer_fold_definitions
from football_prediction_v19.analysis.v2140_goal_probability_outputs import attach_probability_outputs
from football_prediction_v19.analysis.v2150_enriched_challenger import (
    BASE_MODEL, ablation_definitions, fit_enriched_pair, predict_enriched_pair,
)


def enriched_outer_folds(dataset: pd.DataFrame) -> list[dict[str, object]]:
    folds = outer_fold_definitions(dataset)
    for competition in sorted(dataset["competition"].unique()):
        competition_rows = dataset[dataset["competition"].eq(competition)].sort_values("match_date")
        latest_season = sorted(competition_rows["season"].unique())[-1]
        season_rows = competition_rows[competition_rows["season"].eq(latest_season)]
        split = max(1, int(len(season_rows) * .8))
        cutoff = season_rows.iloc[split]["match_date"] if split < len(season_rows) else season_rows.iloc[-1]["match_date"]
        holdout = dataset["competition"].eq(competition) & dataset["season"].eq(latest_season) & dataset["match_date"].ge(cutoff)
        train = dataset["competition"].eq(competition) & dataset["match_date"].lt(cutoff)
        folds.append({
            "fold_type": "CHRONO_LATE_SEASON", "holdout": f"{competition}_{latest_season}_LATE",
            "train_mask": train, "holdout_mask": holdout,
        })
    return folds


def run_enriched_validation(
    dataset: pd.DataFrame,
    frozen_dc: pd.DataFrame,
    passing_groups: list[str],
) -> dict[str, object]:
    definitions = ablation_definitions(passing_groups)
    prediction_parts = defaultdict(list)
    outer_rows = []
    failures = 0
    for fold in enriched_outer_folds(dataset):
        train = dataset[fold["train_mask"]].copy()
        holdout = dataset[fold["holdout_mask"]].copy()
        baseline = _frozen_dc_for_holdout(holdout, frozen_dc)
        baseline["fold_type"], baseline["outer_holdout"] = fold["fold_type"], fold["holdout"]
        prediction_parts[BASE_MODEL].append(baseline)
        base_metrics = evaluate_predictions(baseline.assign(model_name=BASE_MODEL), BASE_MODEL)
        outer_rows.append(_record(fold, train, holdout, definitions[0], base_metrics, 0.0))
        for definition in definitions[1:]:
            try:
                models = fit_enriched_pair(train, definition)
                home, away, clipped = predict_enriched_pair(models, holdout, definition["feature_groups"])
                predictions = attach_probability_outputs(
                    holdout, home, away, model_name=definition["model_name"],
                    model_parameters=json.dumps({
                        "model_class": definition["model_class"],
                        "feature_groups": definition["feature_groups"],
                    }, sort_keys=True),
                    clipped=clipped,
                )
                predictions["fold_type"], predictions["outer_holdout"] = fold["fold_type"], fold["holdout"]
                prediction_parts[definition["model_name"]].append(predictions)
                metrics = evaluate_predictions(predictions, definition["model_name"])
                importance = _group_permutation_importance(
                    models, holdout, definition, home, away,
                )
                outer_rows.append(_record(fold, train, holdout, definition, metrics, importance))
            except Exception as exc:
                failures += 1
                outer_rows.append({
                    "fold_type": fold["fold_type"], "holdout": fold["holdout"],
                    "model_name": definition["model_name"], "training_failed": True, "failure": str(exc),
                })
    return {
        "definitions": definitions,
        "outer_holdout_summary": pd.DataFrame(outer_rows),
        "predictions_by_model": {
            model: pd.concat(parts, ignore_index=True) for model, parts in prediction_parts.items()
        },
        "training_failure_count": failures,
    }


def ablation_summary(validation: dict[str, object]) -> pd.DataFrame:
    outer = validation["outer_holdout_summary"]
    predictions_by_model = validation["predictions_by_model"]
    rows = []
    baseline_outer = outer[outer["model_name"].eq(BASE_MODEL)][
        ["fold_type", "holdout", "total_goals_mae", "multiclass_brier_score", "btts_brier_score",
         "over_1_5_brier_score", "over_2_5_brier_score", "over_3_5_brier_score",
         "exact_score_top3_hit_rate", "exact_score_top5_hit_rate"]
    ].rename(columns={column: f"baseline_{column}" for column in outer.columns if column in {
        "total_goals_mae", "multiclass_brier_score", "btts_brier_score",
        "over_1_5_brier_score", "over_2_5_brier_score", "over_3_5_brier_score",
        "exact_score_top3_hit_rate", "exact_score_top5_hit_rate",
    }})
    for definition in validation["definitions"]:
        model = definition["model_name"]
        model_outer = outer[outer["model_name"].eq(model)]
        merged = model_outer.merge(baseline_outer, on=["fold_type", "holdout"])
        changes = merged["baseline_total_goals_mae"] - merged["total_goals_mae"]
        loco = predictions_by_model[model]
        loco = loco[loco["fold_type"].eq("LOCO")].assign(model_name=model)
        baseline_loco = predictions_by_model[BASE_MODEL]
        baseline_loco = baseline_loco[baseline_loco["fold_type"].eq("LOCO")].assign(model_name=BASE_MODEL)
        metrics = evaluate_predictions(loco, model)
        base_hit = baseline_loco["top_probability_outcome"].eq(baseline_loco["actual_result"]).to_numpy()
        model_hit = loco["top_probability_outcome"].eq(loco["actual_result"]).to_numpy()
        corrected = int((~base_hit & model_hit).sum())
        broken = int((base_hit & ~model_hit).sum())
        contribution = _contribution_shares(loco, baseline_loco)
        rows.append({
            "model_name": model, "feature_groups": json.dumps(definition["feature_groups"]),
            "model_class": definition["model_class"], "outer_holdout_count": len(model_outer),
            "mean_holdout_metric_improvement": float(changes.mean()),
            "median_holdout_improvement": float(changes.median()),
            "positive_holdout_count": int(changes.gt(0).sum()),
            "negative_holdout_count": int(changes.lt(0).sum()),
            "positive_holdout_rate": float(changes.gt(0).mean()),
            "worst_holdout_degradation": float(changes.min()),
            "mean_group_permutation_importance": float(model_outer["group_permutation_importance"].mean()),
            "newly_corrected_count": corrected, "newly_broken_count": broken,
            "net_corrected_count": corrected - broken, **contribution,
            **{key: value for key, value in metrics.items() if key != "model_name"},
        })
    return pd.DataFrame(rows)


def _group_permutation_importance(models, holdout, definition, original_home, original_away):
    groups = list(definition["feature_groups"])
    if not groups or holdout.empty:
        return 0.0
    shuffled = holdout.copy()
    rng = np.random.default_rng(2150)
    from football_prediction_v19.analysis.v2150_feature_coverage import GROUP_FEATURES
    columns = [feature for group in groups for feature in GROUP_FEATURES[group]]
    for column in columns:
        shuffled[column] = rng.permutation(shuffled[column].to_numpy())
    home, away, _ = predict_enriched_pair(models, shuffled, groups)
    actual = holdout["actual_home_goals"].to_numpy() + holdout["actual_away_goals"].to_numpy()
    original_mae = float(np.mean(np.abs(actual - original_home - original_away)))
    shuffled_mae = float(np.mean(np.abs(actual - home - away)))
    return shuffled_mae - original_mae


def _record(fold, train, holdout, definition, metrics, importance):
    return {
        "fold_type": fold["fold_type"], "holdout": fold["holdout"],
        "model_name": definition["model_name"], "feature_groups": json.dumps(definition["feature_groups"]),
        "model_class": definition["model_class"], "selection_source": "COVERAGE_GATE_ONLY",
        "holdout_used_for_selection": False, "training_row_count": len(train), "holdout_row_count": len(holdout),
        "training_competitions": json.dumps(sorted(train["competition"].unique().tolist())),
        "training_seasons": json.dumps(sorted(train["season"].unique().tolist())),
        "group_permutation_importance": importance, "training_failed": False,
        **{key: value for key, value in metrics.items() if key not in ("model_name", "rows_evaluated")},
    }


def _contribution_shares(model: pd.DataFrame, baseline: pd.DataFrame) -> dict[str, float]:
    keys = KEYS
    joined = model.merge(
        baseline[keys + ["expected_total_goals"]], on=keys, suffixes=("", "_baseline"),
    )
    actual = joined["actual_home_goals"] + joined["actual_away_goals"]
    joined["advantage"] = (
        (actual - joined["expected_total_goals_baseline"]).abs()
        - (actual - joined["expected_total_goals"]).abs()
    ).clip(lower=0)
    total = float(joined["advantage"].sum())
    if total <= 0:
        return {
            "competition_contribution_share": 0.0, "team_contribution_share": 0.0,
            "season_contribution_share": 0.0,
        }
    teams = pd.concat([
        joined[["home_team", "advantage"]].rename(columns={"home_team": "team"}),
        joined[["away_team", "advantage"]].rename(columns={"away_team": "team"}),
    ]).groupby("team")["advantage"].sum()
    return {
        "competition_contribution_share": float(joined.groupby("competition")["advantage"].sum().max() / total),
        "team_contribution_share": float(teams.max() / (2 * total)),
        "season_contribution_share": float(joined.groupby("season")["advantage"].sum().max() / total),
    }
