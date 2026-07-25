# -*- coding: utf-8 -*-
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from football_prediction_v19.analysis.v2130_poisson_models import poisson_deviance


EPSILON = 1e-15


def evaluate_predictions(rows: pd.DataFrame, model_name: str) -> dict[str, object]:
    frame = rows[rows["model_name"].eq(model_name)].copy()
    n = len(frame)
    if not n:
        return {"model_name": model_name, "rows_evaluated": 0}
    actual_home = frame["actual_home_goals"].astype(float)
    actual_away = frame["actual_away_goals"].astype(float)
    predicted_home = frame["expected_home_goals"].astype(float)
    predicted_away = frame["expected_away_goals"].astype(float)
    actual_total = actual_home + actual_away
    predicted_total = predicted_home + predicted_away
    winner_probs = frame[["home_win_probability", "draw_probability", "away_win_probability"]].to_numpy(float)
    winner_actual = np.array([[result == outcome for outcome in ("HOME", "DRAW", "AWAY")] for result in frame["actual_result"]], float)
    btts_actual = ((actual_home > 0) & (actual_away > 0)).astype(int)
    btts_prob = frame["btts_yes_probability"].astype(float)
    btts_pred = btts_prob >= 0.5
    tp = int((btts_pred & btts_actual.eq(1)).sum())
    fp = int((btts_pred & btts_actual.eq(0)).sum())
    fn = int((~btts_pred & btts_actual.eq(1)).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    actual_scores = [f"{int(home)}-{int(away)}" for home, away in zip(actual_home, actual_away)]
    actual_score_prob = np.array([
        _actual_score_probability(row, score) for (_, row), score in zip(frame.iterrows(), actual_scores)
    ])
    actual_bucket = np.where(actual_total <= 1, "0_1", np.where(actual_total <= 3, "2_3", "4_PLUS"))
    bucket_probs = frame[[
        "total_goals_0_1_probability", "total_goals_2_3_probability", "total_goals_4_plus_probability"
    ]].to_numpy(float)
    bucket_actual = np.array([[bucket == value for value in ("0_1", "2_3", "4_PLUS")] for bucket in actual_bucket], float)
    metrics: dict[str, object] = {
        "model_name": model_name,
        "rows_evaluated": n,
        "home_goals_mae": _mean_abs(actual_home, predicted_home),
        "away_goals_mae": _mean_abs(actual_away, predicted_away),
        "total_goals_mae": _mean_abs(actual_total, predicted_total),
        "home_goals_rmse": _rmse(actual_home, predicted_home),
        "away_goals_rmse": _rmse(actual_away, predicted_away),
        "poisson_deviance": round(float(np.mean([
            poisson_deviance(home, ph) + poisson_deviance(away, pa)
            for home, away, ph, pa in zip(actual_home, actual_away, predicted_home, predicted_away)
        ])), 6),
        "mean_actual_total_goals": round(float(actual_total.mean()), 6),
        "mean_predicted_total_goals": round(float(predicted_total.mean()), 6),
        "top_outcome_hit_rate": round(float(frame["top_probability_outcome"].eq(frame["actual_result"]).mean()), 6),
        "multiclass_brier_score": round(float(np.mean(np.sum((winner_probs - winner_actual) ** 2, axis=1))), 6),
        "multiclass_log_loss": round(float(-np.mean(np.sum(winner_actual * np.log(np.clip(winner_probs, EPSILON, 1)), axis=1))), 6),
        "draw_top_count": int(frame["top_probability_outcome"].eq("DRAW").sum()),
        "actual_draw_count": int(frame["actual_result"].eq("DRAW").sum()),
        "btts_brier_score": round(float(np.mean((btts_prob - btts_actual) ** 2)), 6),
        "btts_log_loss": _binary_log_loss(btts_actual, btts_prob),
        "btts_accuracy": round(float(btts_pred.eq(btts_actual.astype(bool)).mean()), 6),
        "btts_precision": round(precision, 6),
        "btts_recall": round(recall, 6),
        "btts_f1": round(2 * precision * recall / (precision + recall), 6) if precision + recall else 0.0,
        "goal_bucket_hit_rate": round(float(np.mean(np.argmax(bucket_probs, axis=1) == np.argmax(bucket_actual, axis=1))), 6),
        "goal_bucket_brier_score": round(float(np.mean(np.sum((bucket_probs - bucket_actual) ** 2, axis=1))), 6),
        "exact_score_top1_hit_rate": round(float(np.mean([score == row["top_scoreline"] for (_, row), score in zip(frame.iterrows(), actual_scores)])), 6),
        "exact_score_top3_hit_rate": round(float(np.mean([score in row["top_3_scorelines"] for (_, row), score in zip(frame.iterrows(), actual_scores)])), 6),
        "exact_score_top5_hit_rate": round(float(np.mean([score in row["top_5_scorelines"] for (_, row), score in zip(frame.iterrows(), actual_scores)])), 6),
        "average_probability_of_actual_scoreline": round(float(actual_score_prob.mean()), 6),
        "scoreline_log_loss": round(float(-np.log(np.clip(actual_score_prob, EPSILON, 1)).mean()), 6),
        "probability_output_rate": round(float(frame["probability_valid"].mean()), 6),
        "ready_quality_rate": round(float(frame["history_quality"].eq("READY").mean()), 6),
        "low_history_rate": round(float(frame["history_quality"].eq("LOW_HISTORY").mean()), 6),
        "fallback_rate": round(float(frame["fallback_applied"].mean()), 6),
    }
    for outcome in ("HOME", "DRAW", "AWAY"):
        selected = frame["top_probability_outcome"].eq(outcome)
        metrics[f"{outcome.lower()}_top_hit_rate"] = round(float(frame.loc[selected, "actual_result"].eq(outcome).mean()), 6) if selected.any() else 0.0
    for line in ("1_5", "2_5", "3_5"):
        threshold = float(line.replace("_", "."))
        actual = (actual_total > threshold).astype(int)
        probability = frame[f"over_{line}_probability"].astype(float)
        metrics[f"over_{line}_brier_score"] = round(float(np.mean((probability - actual) ** 2)), 6)
        metrics[f"over_{line}_log_loss"] = _binary_log_loss(actual, probability)
        metrics[f"over_{line}_accuracy"] = round(float((probability.ge(0.5)).eq(actual.astype(bool)).mean()), 6)
    return metrics


def build_holdout_summary(predictions: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    folds: list[dict[str, object]] = []
    definitions: list[tuple[str, str, pd.Series, pd.Series]] = []
    premier = predictions["competition"].eq("Premier League")
    for season in sorted(predictions.loc[premier, "season"].unique()):
        holdout_mask = premier & predictions["season"].eq(season)
        definitions.append(("LOSO", str(season), holdout_mask, premier & ~holdout_mask))
    for competition in sorted(predictions["competition"].unique()):
        holdout_mask = predictions["competition"].eq(competition)
        definitions.append(("LOCO", str(competition), holdout_mask, ~holdout_mask))
    for fold_type, holdout, holdout_mask, training_mask in definitions:
        train = predictions[training_mask]
        training_metrics = [evaluate_predictions(train, name) for name in sorted(train["model_name"].unique())]
        usable = [metric for metric in training_metrics if metric.get("rows_evaluated", 0)]
        selected = min(usable, key=lambda metric: (metric["total_goals_mae"], metric["multiclass_brier_score"]))["model_name"]
        holdout_metrics = evaluate_predictions(predictions[holdout_mask], str(selected))
        baseline = evaluate_predictions(predictions[holdout_mask], "ROLLING_LEAGUE_MEAN_POISSON")
        folds.append({
            "fold_type": fold_type, "holdout": holdout, "selected_model_name": selected,
            "selection_source": "TRAINING_ONLY", "training_rows": int(len(train[train["model_name"].eq(selected)])),
            "holdout_rows": int(holdout_metrics.get("rows_evaluated", 0)),
            "holdout_total_goals_mae": holdout_metrics.get("total_goals_mae", 0.0),
            "baseline_total_goals_mae": baseline.get("total_goals_mae", 0.0),
            "goal_mae_improvement": round(float(baseline.get("total_goals_mae", 0)) - float(holdout_metrics.get("total_goals_mae", 0)), 6),
            "holdout_btts_brier": holdout_metrics.get("btts_brier_score", 0.0),
            "baseline_btts_brier": baseline.get("btts_brier_score", 0.0),
            "positive": float(holdout_metrics.get("total_goals_mae", 0)) < float(baseline.get("total_goals_mae", 0)),
            "holdout_used_for_selection": False,
        })
    summary = pd.DataFrame(folds)
    selections = summary["selected_model_name"].value_counts()
    best = sorted(selections[selections.eq(selections.max())].index)[0]
    return summary, str(best)


def _mean_abs(actual: pd.Series, predicted: pd.Series) -> float:
    return round(float(np.mean(np.abs(actual - predicted))), 6)


def _rmse(actual: pd.Series, predicted: pd.Series) -> float:
    return round(float(np.sqrt(np.mean((actual - predicted) ** 2))), 6)


def _binary_log_loss(actual: pd.Series, probability: pd.Series) -> float:
    p = np.clip(np.asarray(probability, float), EPSILON, 1 - EPSILON)
    y = np.asarray(actual, float)
    return round(float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))), 6)


def _actual_score_probability(row: pd.Series, score: str) -> float:
    for item in row["ranked_scorelines"]:
        if item["scoreline"] == score:
            return float(item["probability"])
    return EPSILON
