# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v2130_goal_model_evaluation import evaluate_predictions


def failure_audit(predictions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for model, group in predictions.groupby("model_name"):
        rows.append({
            "model_name": model, "rows_evaluated": len(group),
            "fallback_count": int(group["fallback_reason"].ne("").sum()),
            "fallback_rate": float(group["fallback_reason"].ne("").mean()),
            "low_history_count": int(group["history_quality"].ne("READY").sum()),
            "ready_count": int(group["history_quality"].eq("READY").sum()),
            "average_expected_home_goals": group["expected_home_goals"].mean(),
            "average_expected_away_goals": group["expected_away_goals"].mean(),
            "average_expected_total_goals": group["expected_total_goals"].mean(),
            "actual_average_home_goals": group["actual_home_goals"].mean(),
            "actual_average_away_goals": group["actual_away_goals"].mean(),
            "actual_average_total_goals": (group["actual_home_goals"] + group["actual_away_goals"]).mean(),
            "lambda_home_min": group["expected_home_goals"].min(), "lambda_home_max": group["expected_home_goals"].max(),
            "lambda_home_mean": group["expected_home_goals"].mean(), "lambda_away_min": group["expected_away_goals"].min(),
            "lambda_away_max": group["expected_away_goals"].max(), "lambda_away_mean": group["expected_away_goals"].mean(),
            "invalid_lambda_count": int((~group["expected_home_goals"].between(.15, 4.5) | ~group["expected_away_goals"].between(.15, 4.5)).sum()),
            "clipped_lambda_count": int((group["lambda_home_clipped"] | group["lambda_away_clipped"]).sum()),
            "zero_variance_feature_count": int(group[["expected_home_goals", "expected_away_goals"]].nunique().eq(1).sum()),
            "team_strength_available_rate": float((group["home_prior_matches_count"].gt(0) & group["away_prior_matches_count"].gt(0)).mean()),
            "venue_strength_available_rate": float(group["venue_history_ready"].mean()),
            "form_available_rate": float(group["form_available"].mean()),
            "opponent_adjustment_available_rate": float(group["opponent_adjustment_available"].mean()),
        })
    return pd.DataFrame(rows)


def model_difference_audit(predictions: pd.DataFrame, baseline: str) -> pd.DataFrame:
    keys = ["competition", "season", "match_date", "home_team", "away_team"]
    base = predictions[predictions["model_name"].eq(baseline)][keys + ["expected_home_goals", "expected_away_goals"]]
    rows = []
    for model, group in predictions.groupby("model_name"):
        joined = group.merge(base, on=keys, suffixes=("", "_baseline"))
        identical = (
            joined["expected_home_goals"].eq(joined["expected_home_goals_baseline"])
            & joined["expected_away_goals"].eq(joined["expected_away_goals_baseline"])
        )
        rows.append({
            "model_name": model, "comparison_model": baseline, "rows_compared": len(joined),
            "identical_lambda_pair_count": int(identical.sum()),
            "different_lambda_pair_count": int((~identical).sum()),
            "identical_prediction_row_count": int((
                identical & joined["top_probability_outcome"].eq(
                    joined.get("top_probability_outcome_baseline", joined["top_probability_outcome"])
                )
            ).sum()),
            "baseline_reproduction_rate": float(identical.mean()) if len(joined) else 0.0,
        })
    return pd.DataFrame(rows)


def select_training_only_holdouts(predictions: pd.DataFrame, baseline: str) -> pd.DataFrame:
    folds = []
    definitions = []
    premier = predictions["competition"].eq("Premier League")
    for season in sorted(predictions.loc[premier, "season"].unique()):
        holdout = premier & predictions["season"].eq(season)
        definitions.append(("LOSO", str(season), holdout, premier & ~holdout))
    for competition in sorted(predictions["competition"].unique()):
        holdout = predictions["competition"].eq(competition)
        definitions.append(("LOCO", str(competition), holdout, ~holdout))
    names = list(predictions["model_name"].unique())
    complexity = {name: index for index, name in enumerate(names)}
    for fold_type, label, holdout_mask, train_mask in definitions:
        training_metrics = [evaluate_predictions(predictions[train_mask], name) for name in names]
        best_mae = min(float(metric["total_goals_mae"]) for metric in training_metrics)
        eligible = [metric for metric in training_metrics if float(metric["total_goals_mae"]) <= best_mae * 1.005]
        chosen = min(eligible, key=lambda metric: (
            float(metric["poisson_deviance"]), float(metric["btts_brier_score"]),
            float(metric["multiclass_brier_score"]), complexity[str(metric["model_name"])],
        ))
        model = str(chosen["model_name"])
        held = evaluate_predictions(predictions[holdout_mask], model)
        base = evaluate_predictions(predictions[holdout_mask], baseline)
        folds.append({
            "fold_type": fold_type, "holdout": label, "selected_model_name": model,
            "selection_source": "TRAINING_ONLY", "holdout_used_for_selection": False,
            "training_rows": int(train_mask.sum() / len(names)), "holdout_rows": int(held["rows_evaluated"]),
            "best_total_goals_mae": held["total_goals_mae"], "baseline_total_goals_mae": base["total_goals_mae"],
            "total_goals_mae_improvement": round(float(base["total_goals_mae"]) - float(held["total_goals_mae"]), 6),
            "best_btts_brier_score": held["btts_brier_score"], "baseline_btts_brier_score": base["btts_brier_score"],
            "best_over_2_5_brier_score": held["over_2_5_brier_score"], "baseline_over_2_5_brier_score": base["over_2_5_brier_score"],
            "positive": float(held["total_goals_mae"]) < float(base["total_goals_mae"]),
        })
    return pd.DataFrame(folds)
