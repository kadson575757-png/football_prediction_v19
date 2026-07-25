"""Nested validation and reporting for the v2.18.0 hierarchical challenger."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from football_prediction_v19.analysis.v2130_score_matrix import build_score_matrix, derive_distribution
from football_prediction_v19.analysis.v2131_repaired_goal_models import repaired_lambdas
from football_prediction_v19.analysis.v2140_goal_ml_dataset import load_v2140_dataset
from football_prediction_v19.analysis.v2180_cross_fitted_predictions import (
    chronological_oof_predictions,
    complete_oof_with_prior,
)
from football_prediction_v19.analysis.v2180_dynamic_rating import build_rating_features, candidate_configs
from football_prediction_v19.analysis.v2180_hierarchical_winner import (
    ABLATIONS,
    fit_hierarchical_model,
    predict_hierarchical,
)
from football_prediction_v19.analysis.v2180_meta_winner import (
    fit_meta_model,
    meta_candidates,
    meta_features,
    predict_meta_model,
)


OUTCOMES = np.array(["HOME", "DRAW", "AWAY"])
SAFETY = {
    "automatic_betting_enabled": False,
    "staking_logic_enabled": False,
    "roi_logic_enabled": False,
    "productive_betting_enabled": False,
}
GOAL_CONFIG = {
    "family": "DIXON_COLES_ON_BEST_BASE", "shrinkage_weight": 10,
    "form_window": 0, "form_weight": 0.0, "rho": -0.10,
}
DEFAULT_OUTPUT_DIR = "outputs/v2180_hierarchical_winner_challenger"


def prepare_challenger_dataset(project_root: str | Path) -> pd.DataFrame:
    rows = load_v2140_dataset(project_root).copy()
    rows["match_date"] = pd.to_datetime(rows["match_date"])
    primary = rows[["base_home_probability", "base_draw_probability", "base_away_probability"]].to_numpy(float)
    missing = ~np.isfinite(primary).all(axis=1)
    primary[missing] = np.array([0.34, 0.32, 0.34])
    primary = np.clip(primary, 1e-9, None)
    primary /= primary.sum(axis=1, keepdims=True)
    rows[["base_home_probability", "base_draw_probability", "base_away_probability"]] = primary
    rows["base_probability_edge"] = np.sort(primary, axis=1)[:, -1] - np.sort(primary, axis=1)[:, -2]
    goal_records = []
    for _, feature in rows.iterrows():
        lambdas = repaired_lambdas(feature, GOAL_CONFIG)
        matrix, _ = build_score_matrix(
            lambdas["expected_home_goals"], lambdas["expected_away_goals"], max_goals=10, rho=-0.10
        )
        distribution = derive_distribution(matrix)
        goal_records.append({
            "expected_home_goals": lambdas["expected_home_goals"],
            "expected_away_goals": lambdas["expected_away_goals"],
            "goal_home_probability": distribution["home_win_probability"],
            "goal_draw_probability": distribution["draw_probability"],
            "goal_away_probability": distribution["away_win_probability"],
            "low_score_probability": distribution["total_goals_0_1_probability"],
        })
    rows = pd.concat([rows.reset_index(drop=True), pd.DataFrame(goal_records)], axis=1)
    rows["model_agreement"] = (
        primary.argmax(axis=1)
        == rows[["goal_home_probability", "goal_draw_probability", "goal_away_probability"]].to_numpy().argmax(axis=1)
    ).astype(int)
    rows["maximum_model_probability_difference"] = np.max(np.abs(
        primary - rows[["goal_home_probability", "goal_draw_probability", "goal_away_probability"]].to_numpy()
    ), axis=1)
    rows["rolling_league_draw_rate"] = _prior_expanding_rate(rows, ["competition"], "DRAW")
    rows["rolling_league_home_rate"] = _prior_expanding_rate(rows, ["competition"], "HOME")
    rows["rolling_league_away_rate"] = _prior_expanding_rate(rows, ["competition"], "AWAY")
    league_total = rows[["rolling_league_home_rate", "rolling_league_draw_rate", "rolling_league_away_rate"]].sum(axis=1)
    rows[["rolling_league_home_rate", "rolling_league_draw_rate", "rolling_league_away_rate"]] = rows[[
        "rolling_league_home_rate", "rolling_league_draw_rate", "rolling_league_away_rate"
    ]].div(league_total, axis=0)
    rows["home_team_draw_rate"] = _team_prior_draw_rate(rows, "home_team")
    rows["away_team_draw_rate"] = _team_prior_draw_rate(rows, "away_team")
    rows["history_quality_numeric"] = np.minimum(rows["home_prior_matches_count"], rows["away_prior_matches_count"]).clip(upper=20) / 20
    rows["maximum_source_timestamp"] = rows["maximum_source_date"].map(
        lambda value: f"{value}T23:59:59" if value else ""
    )
    return rows.reset_index(drop=True)


def outer_holdouts(rows: pd.DataFrame) -> list[dict]:
    definitions = []
    for season in sorted(rows["season"].astype(str).unique()):
        definitions.append({"fold_type": "LEAVE_ONE_SEASON_OUT", "holdout": season, "test": rows["season"].astype(str).eq(season)})
    for competition in sorted(rows["competition"].astype(str).unique()):
        definitions.append({"fold_type": "LEAVE_ONE_COMPETITION_OUT", "holdout": competition, "test": rows["competition"].astype(str).eq(competition)})
    chronological = pd.Series(False, index=rows.index)
    for _, group in rows.groupby(["competition", "season"]):
        ordered = group.sort_values("match_date")
        chronological.loc[ordered.index[int(len(ordered) * 0.8):]] = True
    definitions.append({"fold_type": "CHRONOLOGICAL_LAST_SEGMENT", "holdout": "LAST_20_PERCENT", "test": chronological})
    return definitions


def run_validation(project_root: str | Path, output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = prepare_challenger_dataset(project_root)
    holdouts = outer_holdouts(rows)
    slim = rows[[
        "competition", "season", "match_date", "home_team", "away_team",
        "actual_home_goals", "actual_away_goals", "actual_result",
    ]].copy()
    selected_ratings, rating_selection = _select_ratings(slim, holdouts)
    rating_cache = {
        name: build_rating_features(slim, next(config for config in candidate_configs() if config["config_name"] == name))
        for name in sorted(set(selected_ratings.values()))
    }
    prediction_frames, holdout_rows, oof_audits, ablations, meta_summaries = [], [], [], [], []
    for fold_number, definition in enumerate(holdouts, start=1):
        test_mask = definition["test"].to_numpy(bool)
        train_idx, test_idx = np.flatnonzero(~test_mask), np.flatnonzero(test_mask)
        if not len(test_idx) or len(train_idx) < 100:
            continue
        rating_name = selected_ratings[fold_number]
        fold_rows = _attach_rating(rows, rating_cache[rating_name])
        groups, c, inner_scores = _select_hierarchical(fold_rows.iloc[train_idx])
        for record in inner_scores:
            ablations.append({"outer_fold": fold_number, **record})
        oof, audit = chronological_oof_predictions(fold_rows.iloc[train_idx].reset_index(drop=True), feature_groups=groups, c=c)
        oof = complete_oof_with_prior(fold_rows.iloc[train_idx].reset_index(drop=True), oof)
        audit["outer_fold"] = fold_number
        audit["outer_holdout"] = definition["holdout"]
        oof_audits.append(audit)
        hierarchy = fit_hierarchical_model(fold_rows.iloc[train_idx], groups, c)
        hierarchy_test = predict_hierarchical(hierarchy, fold_rows.iloc[test_idx])
        x_meta = meta_features(fold_rows.iloc[train_idx].reset_index(drop=True), oof)
        meta_name, meta_params = _select_meta(x_meta, fold_rows.iloc[train_idx]["actual_result"].reset_index(drop=True))
        meta = fit_meta_model(x_meta, fold_rows.iloc[train_idx]["actual_result"].reset_index(drop=True), meta_name, meta_params)
        x_test = meta_features(fold_rows.iloc[test_idx].reset_index(drop=True), hierarchy_test)
        challenger = predict_meta_model(meta, x_test)
        simplified = _simplified_meta_predictions(
            x_meta,
            fold_rows.iloc[train_idx]["actual_result"].reset_index(drop=True),
            x_test,
        )
        predicted = _prediction_frame(
            fold_rows.iloc[test_idx], challenger, hierarchy_test, simplified,
            fold_number, definition, rating_name, groups, meta_name,
        )
        prediction_frames.append(predicted)
        baseline_metrics = metrics(
            predicted["actual_result"],
            predicted[["baseline_home_probability", "baseline_draw_probability", "baseline_away_probability"]].to_numpy(),
        )
        challenger_metrics = metrics(predicted["actual_result"], challenger)
        holdout_rows.append({
            "outer_fold": fold_number, "fold_type": definition["fold_type"], "holdout": definition["holdout"],
            "train_count": len(train_idx), "test_count": len(test_idx),
            "rating_model": rating_name, "feature_groups": groups, "meta_model": meta_name,
            "baseline_hit_rate": baseline_metrics["top_outcome_hit_rate"],
            "challenger_hit_rate": challenger_metrics["top_outcome_hit_rate"],
            "hit_rate_delta": challenger_metrics["top_outcome_hit_rate"] - baseline_metrics["top_outcome_hit_rate"],
            "baseline_brier_score": baseline_metrics["multiclass_brier_score"],
            "challenger_brier_score": challenger_metrics["multiclass_brier_score"],
            "baseline_log_loss": baseline_metrics["multiclass_log_loss"],
            "challenger_log_loss": challenger_metrics["multiclass_log_loss"],
            "outer_holdout_used_for_selection": False,
        })
        meta_summaries.append({"outer_fold": fold_number, "model_name": meta_name, "parameters": json.dumps(meta_params), "feature_count": x_meta.shape[1]})
    predictions = pd.concat(prediction_frames, ignore_index=True)
    outer = pd.DataFrame(holdout_rows)
    oof_audit = pd.concat(oof_audits, ignore_index=True)
    baseline_probs = predictions[["baseline_home_probability", "baseline_draw_probability", "baseline_away_probability"]].to_numpy()
    challenger_probs = predictions[["challenger_home_probability", "challenger_draw_probability", "challenger_away_probability"]].to_numpy()
    baseline = metrics(predictions["actual_result"], baseline_probs)
    challenger = metrics(predictions["actual_result"], challenger_probs)
    corrections = _correction_audits(predictions)
    summary = _summary(rows, predictions, outer, oof_audit, baseline, challenger, corrections, rating_selection)
    _write_outputs(out, rows, predictions, outer, oof_audit, pd.DataFrame(ablations), pd.DataFrame(meta_summaries), baseline, challenger, corrections, summary)
    summary["output_dir"] = str(out.resolve())
    return summary


def metrics(actual: pd.Series, probabilities: np.ndarray) -> dict:
    target = pd.Categorical(actual, categories=OUTCOMES).codes
    predicted = probabilities.argmax(axis=1)
    onehot = np.eye(3)[target]
    draw_pred = predicted == 1
    draw_actual = target == 1
    draw_tp = int(np.sum(draw_pred & draw_actual))
    draw_precision = draw_tp / max(1, int(draw_pred.sum()))
    draw_recall = draw_tp / max(1, int(draw_actual.sum()))
    return {
        "top_outcome_hit_rate": float(np.mean(predicted == target)),
        "multiclass_brier_score": float(np.mean(np.sum((probabilities - onehot) ** 2, axis=1))),
        "multiclass_log_loss": float(-np.mean(np.log(np.clip(probabilities[np.arange(len(target)), target], 1e-12, 1)))),
        "home_top_count": int(np.sum(predicted == 0)), "draw_top_count": int(draw_pred.sum()), "away_top_count": int(np.sum(predicted == 2)),
        "home_hit_rate": _class_recall(target, predicted, 0), "draw_hit_rate": draw_recall, "away_hit_rate": _class_recall(target, predicted, 2),
        "draw_precision": draw_precision, "draw_recall": draw_recall,
        "draw_f1": 2 * draw_precision * draw_recall / max(1e-12, draw_precision + draw_recall),
        "invalid_probability_count": int(np.sum(~np.isfinite(probabilities).all(axis=1) | (np.abs(probabilities.sum(axis=1) - 1) > 1e-9))),
    }


def _select_ratings(slim: pd.DataFrame, holdouts: list[dict]) -> tuple[dict[int, str], pd.DataFrame]:
    best = {index: (-1.0, "") for index in range(1, len(holdouts) + 1)}
    records = []
    for config in candidate_configs():
        rated = build_rating_features(slim, config)
        probs = rated[["rating_home_probability", "rating_draw_probability", "rating_away_probability"]].to_numpy()
        target = pd.Categorical(rated["actual_result"], categories=OUTCOMES).codes
        for index, definition in enumerate(holdouts, start=1):
            train = np.flatnonzero(~definition["test"].to_numpy(bool))
            inner = train[int(len(train) * 0.8):]
            score = float(np.mean(probs[inner].argmax(axis=1) == target[inner])) if len(inner) else 0.0
            records.append({"outer_fold": index, "rating_config": config["config_name"], "inner_hit_rate": score})
            if (score, config["config_name"]) > best[index]:
                best[index] = (score, config["config_name"])
    return {index: value[1] for index, value in best.items()}, pd.DataFrame(records)


def _attach_rating(rows: pd.DataFrame, rating: pd.DataFrame) -> pd.DataFrame:
    result = rows.copy()
    columns = [
        "rating_home_probability", "rating_draw_probability", "rating_away_probability",
        "home_rating", "away_rating", "rating_difference", "rating_home_advantage", "home_venue_rating", "away_venue_rating",
        "rating_momentum_last5", "rating_momentum_last10", "rating_uncertainty", "history_count",
        "season_start_shrinkage_applied", "promoted_team_fallback", "rating_source",
        "fallback_used", "fallback_reason", "uncertainty_level",
    ]
    for column in columns:
        result[column] = rating[column].to_numpy()
    return result


def _select_hierarchical(train: pd.DataFrame) -> tuple[str, float, list[dict]]:
    split = int(len(train) * 0.8)
    inner_train, validation = train.iloc[:split], train.iloc[split:]
    candidates = []
    for groups in ABLATIONS:
        for c in (0.1, 1.0, 10.0):
            model = fit_hierarchical_model(inner_train, groups, c)
            score = metrics(validation["actual_result"], predict_hierarchical(model, validation))
            candidates.append({"feature_groups": groups, "c": c, **score})
    best = max(candidates, key=lambda row: (row["top_outcome_hit_rate"], -row["multiclass_brier_score"], -row["multiclass_log_loss"]))
    return best["feature_groups"], best["c"], candidates


def _select_meta(x: pd.DataFrame, y: pd.Series) -> tuple[str, dict]:
    split = int(len(x) * 0.8)
    scores = []
    for name, params in meta_candidates():
        model = fit_meta_model(x.iloc[:split], y.iloc[:split], name, params)
        probability = predict_meta_model(model, x.iloc[split:])
        score = metrics(y.iloc[split:], probability)
        scores.append((score["top_outcome_hit_rate"], -score["multiclass_brier_score"], -score["multiclass_log_loss"], name, params))
    best = max(scores, key=lambda row: row[:4])
    return best[3], best[4]


def _prediction_frame(rows, challenger, hierarchical, simplified, fold_number, definition, rating_name, groups, meta_name):
    result = rows[["competition", "season", "match_date", "home_team", "away_team", "actual_result", "target_match_date", "maximum_source_date", "maximum_source_timestamp", "post_match_rows_used_count", "asof_clean"]].copy()
    result["outer_fold"] = fold_number
    result["fold_type"], result["outer_holdout"] = definition["fold_type"], definition["holdout"]
    result[["baseline_home_probability", "baseline_draw_probability", "baseline_away_probability"]] = rows[["base_home_probability", "base_draw_probability", "base_away_probability"]].to_numpy()
    result[["goal_home_probability", "goal_draw_probability", "goal_away_probability"]] = rows[["goal_home_probability", "goal_draw_probability", "goal_away_probability"]].to_numpy()
    result[["rating_home_probability", "rating_draw_probability", "rating_away_probability"]] = rows[["rating_home_probability", "rating_draw_probability", "rating_away_probability"]].to_numpy()
    for column in (
        "home_rating", "away_rating", "rating_difference", "rating_home_advantage", "home_venue_rating", "away_venue_rating",
        "rating_momentum_last5", "rating_momentum_last10", "rating_uncertainty", "history_count",
        "season_start_shrinkage_applied", "promoted_team_fallback", "rating_source",
        "fallback_used", "fallback_reason", "uncertainty_level",
    ):
        result[column] = rows[column].to_numpy()
    result[["rolling_home_probability", "rolling_draw_probability", "rolling_away_probability"]] = rows[["rolling_league_home_rate", "rolling_league_draw_rate", "rolling_league_away_rate"]].to_numpy()
    result[["hierarchical_home_probability", "hierarchical_draw_probability", "hierarchical_away_probability"]] = hierarchical
    result[["challenger_home_probability", "challenger_draw_probability", "challenger_away_probability"]] = challenger
    for name, probabilities in simplified.items():
        result[[f"{name}_home_probability", f"{name}_draw_probability", f"{name}_away_probability"]] = probabilities
    result["rating_model"], result["feature_groups"], result["meta_model"] = rating_name, groups, meta_name
    result["oof_base_predictions_used"] = True
    result["outer_holdout_used_for_selection"] = False
    return result


def _simplified_meta_predictions(x_train: pd.DataFrame, y_train: pd.Series, x_test: pd.DataFrame) -> dict[str, np.ndarray]:
    common = ["rating_difference", "base_probability_edge", "season_phase", "history_quality_numeric"]
    variants = {
        "primary_rating_meta": [column for column in x_train if column.startswith(("primary_", "rating_"))] + common,
        "primary_goal_meta": [column for column in x_train if column.startswith(("primary_", "goal_"))] + common,
        "primary_rating_goal_meta": [
            column for column in x_train if column.startswith(("primary_", "rating_", "goal_"))
        ] + common,
    }
    predictions = {}
    for name, columns in variants.items():
        columns = list(dict.fromkeys(columns))
        model = fit_meta_model(
            x_train[columns], y_train,
            "MULTINOMIAL_LOGISTIC_STACKER", {"C": 1.0},
        )
        predictions[name] = predict_meta_model(model, x_test[columns])
    return predictions


def _correction_audits(predictions: pd.DataFrame) -> dict:
    actual = predictions["actual_result"].to_numpy()
    baseline = OUTCOMES[predictions[["baseline_home_probability", "baseline_draw_probability", "baseline_away_probability"]].to_numpy().argmax(axis=1)]
    challenger = OUTCOMES[predictions[["challenger_home_probability", "challenger_draw_probability", "challenger_away_probability"]].to_numpy().argmax(axis=1)]
    newly_correct = (baseline != actual) & (challenger == actual)
    newly_broken = (baseline == actual) & (challenger != actual)
    contribution = predictions.assign(newly_corrected=newly_correct.astype(int), newly_broken=newly_broken.astype(int))
    return {
        "newly_corrected_count": int(newly_correct.sum()),
        "newly_broken_count": int(newly_broken.sum()),
        "net_corrected_count": int(newly_correct.sum() - newly_broken.sum()),
        "rows": contribution,
    }


def _summary(rows, predictions, outer, oof, baseline, challenger, corrections, rating_selection):
    positive = outer["hit_rate_delta"] > 0
    competition_audit = _contribution_table(corrections["rows"], "competition")
    team_rows = pd.concat([
        corrections["rows"].assign(team=corrections["rows"]["home_team"]),
        corrections["rows"].assign(team=corrections["rows"]["away_team"]),
    ])
    team_audit = _contribution_table(team_rows, "team")
    total_positive = max(1, corrections["newly_corrected_count"])
    dominant_comp = max(0.0, float(competition_audit["newly_corrected"].max()) / total_positive)
    dominant_team = max(0.0, float(team_audit["newly_corrected"].max()) / (2 * total_positive))
    hit_delta = challenger["top_outcome_hit_rate"] - baseline["top_outcome_hit_rate"]
    mandatory = (
        challenger["invalid_probability_count"] == 0
        and int(predictions["post_match_rows_used_count"].sum()) == 0
        and rows["competition"].nunique() >= 4 and len(outer) >= 7
        and int(oof["in_sample_prediction_count"].sum()) == 0
        and bool(oof["chronological_clean"].all())
    )
    success = (
        mandatory and hit_delta >= 0.02
        and challenger["multiclass_brier_score"] < baseline["multiclass_brier_score"]
        and challenger["multiclass_log_loss"] < baseline["multiclass_log_loss"]
        and corrections["net_corrected_count"] > 0
        and float(positive.mean()) >= 0.60
        and challenger["draw_recall"] >= baseline["draw_recall"] + 0.10
        and challenger["draw_precision"] >= 0.20
        and dominant_comp <= 0.50 and dominant_team <= 0.25
        and min(challenger["home_top_count"], challenger["draw_top_count"], challenger["away_top_count"]) / len(predictions) >= 0.05
    )
    return {
        "v2180_hierarchical_winner_challenger_status": "READY",
        "rows_loaded": len(rows), "rows_evaluated": len(predictions),
        "competitions_evaluated": int(rows["competition"].nunique()), "seasons_evaluated": int(rows["season"].nunique()),
        "outer_holdout_count": len(outer), "baseline_model_name": "PRIMARY_WINNER_V21_RESULTS_CORE",
        "best_rating_model": rating_selection.groupby("rating_config")["inner_hit_rate"].mean().idxmax(),
        "best_hierarchical_model": "DRAW_NON_DRAW_PLUS_HOME_AWAY",
        "best_meta_model": predictions["meta_model"].mode().iloc[0],
        "best_feature_groups": predictions["feature_groups"].mode().iloc[0],
        "baseline_hit_rate": baseline["top_outcome_hit_rate"], "challenger_hit_rate": challenger["top_outcome_hit_rate"],
        "hit_rate_delta": hit_delta,
        "baseline_brier_score": baseline["multiclass_brier_score"], "challenger_brier_score": challenger["multiclass_brier_score"],
        "brier_improvement": baseline["multiclass_brier_score"] - challenger["multiclass_brier_score"],
        "baseline_log_loss": baseline["multiclass_log_loss"], "challenger_log_loss": challenger["multiclass_log_loss"],
        "log_loss_improvement": baseline["multiclass_log_loss"] - challenger["multiclass_log_loss"],
        "baseline_draw_top_count": baseline["draw_top_count"], "challenger_draw_top_count": challenger["draw_top_count"],
        "baseline_draw_recall": baseline["draw_recall"], "challenger_draw_precision": challenger["draw_precision"],
        "challenger_draw_recall": challenger["draw_recall"], "challenger_draw_f1": challenger["draw_f1"],
        **{key: corrections[key] for key in ("newly_corrected_count", "newly_broken_count", "net_corrected_count")},
        "positive_holdout_rate": float(positive.mean()), "worst_holdout_hit_delta": float(outer["hit_rate_delta"].min()),
        "dominant_competition_share": dominant_comp, "dominant_team_share": dominant_team,
        "probability_output_rate": 1.0, "invalid_probability_count": challenger["invalid_probability_count"],
        "oof_leakage_count": int(oof["in_sample_prediction_count"].sum() + (~oof["chronological_clean"]).sum()),
        "post_match_rows_used_count": int(predictions["post_match_rows_used_count"].sum()),
        "fallback_rate": float(predictions["fallback_used"].mean()),
        "missing_feature_rate": float(rows.isna().mean().mean()),
        "challenger_status": "SHADOW_APPROVED" if success else "DIAGNOSTIC_ONLY",
        "recommendation": "APPROVE_FOR_PROSPECTIVE_SHADOW" if success else "DIAGNOSTIC_ONLY",
        **SAFETY,
    }


def _write_outputs(out, rows, predictions, outer, oof, ablations, meta_summary, baseline, challenger, corrections, summary):
    pd.DataFrame([{
        "feature": column, "available_count": int(rows[column].notna().sum()),
        "availability_rate": float(rows[column].notna().mean()),
    } for column in rows.columns]).to_csv(out / "v2180_feature_availability.csv", index=False)
    rating_cols = ["competition", "season", "match_date", "home_team", "away_team", "target_match_date", "maximum_source_date", "maximum_source_timestamp", "post_match_rows_used_count", "asof_clean"]
    rating_detail = [
        "rating_model", "home_rating", "away_rating", "rating_difference", "rating_home_advantage", "home_venue_rating",
        "away_venue_rating", "rating_momentum_last5", "rating_momentum_last10",
        "rating_uncertainty", "history_count", "season_start_shrinkage_applied",
        "promoted_team_fallback", "rating_source", "fallback_used", "fallback_reason", "uncertainty_level",
    ]
    predictions[rating_cols + rating_detail].to_csv(out / "v2180_rating_audit.csv", index=False)
    predictions[[*rating_cols[:5], "rating_home_probability", "rating_draw_probability", "rating_away_probability"]].to_csv(out / "v2180_rating_predictions.csv", index=False)
    pd.DataFrame([{"model": "DRAW_VS_NON_DRAW", "feature_groups": summary["best_feature_groups"], "draw_precision": challenger["draw_precision"], "draw_recall": challenger["draw_recall"], "draw_f1": challenger["draw_f1"]}]).to_csv(out / "v2180_draw_model_summary.csv", index=False)
    pd.DataFrame([{"model": "HOME_VS_AWAY", "training_scope": "NON_DRAW_ONLY"}]).to_csv(out / "v2180_home_away_model_summary.csv", index=False)
    oof.to_csv(out / "v2180_oof_prediction_audit.csv", index=False)
    meta_summary.to_csv(out / "v2180_meta_model_summary.csv", index=False)
    ablations.to_csv(out / "v2180_feature_group_ablation.csv", index=False)
    outer.to_csv(out / "v2180_outer_holdout_summary.csv", index=False)
    rolling_probabilities = predictions[["rolling_home_probability", "rolling_draw_probability", "rolling_away_probability"]].to_numpy()
    frequent_probabilities = np.full_like(rolling_probabilities, 1e-6)
    frequent_probabilities[np.arange(len(frequent_probabilities)), rolling_probabilities.argmax(axis=1)] = 1.0 - 2e-6
    comparison_rows = [
        {"model": "PRIMARY_WINNER_BASELINE", **baseline},
        {"model": "SUPPORTING_GOAL_MODEL", **metrics(predictions["actual_result"], predictions[["goal_home_probability", "goal_draw_probability", "goal_away_probability"]].to_numpy())},
        {"model": "MOST_FREQUENT_LEAGUE_OUTCOME", **metrics(predictions["actual_result"], frequent_probabilities)},
        {"model": "ROLLING_LEAGUE_DISTRIBUTION", **metrics(predictions["actual_result"], rolling_probabilities)},
        {"model": "RATING_MODEL_ONLY", **metrics(predictions["actual_result"], predictions[["rating_home_probability", "rating_draw_probability", "rating_away_probability"]].to_numpy())},
        {"model": "HIERARCHICAL_MODEL_ONLY", **metrics(predictions["actual_result"], predictions[["hierarchical_home_probability", "hierarchical_draw_probability", "hierarchical_away_probability"]].to_numpy())},
        {"model": "HIERARCHICAL_META_CHALLENGER", **challenger},
    ]
    pd.DataFrame(comparison_rows).to_csv(out / "v2180_model_comparison.csv", index=False)
    predictions.to_csv(out / "v2180_match_predictions.csv", index=False)
    _confusion(predictions).to_csv(out / "v2180_confusion_matrix.csv", index=False)
    _calibration(predictions).to_csv(out / "v2180_calibration.csv", index=False)
    team_rows = pd.concat([corrections["rows"].assign(team=corrections["rows"]["home_team"]), corrections["rows"].assign(team=corrections["rows"]["away_team"])])
    _contribution_table(team_rows, "team").to_csv(out / "v2180_team_contribution_audit.csv", index=False)
    _contribution_table(corrections["rows"], "competition").to_csv(out / "v2180_competition_contribution_audit.csv", index=False)
    predictions[rating_cols].to_csv(out / "v2180_asof_audit.csv", index=False)
    (out / "v2180_summary.json").write_text(json.dumps(summary, indent=2, default=_json_default) + "\n", encoding="utf-8")
    (out / "v2180_report.md").write_text(_report(summary), encoding="utf-8")


def _prior_expanding_rate(rows, groups, outcome):
    result = pd.Series(index=rows.index, dtype=float)
    for _, group in rows.sort_values("match_date").groupby(groups):
        values = group["actual_result"].eq(outcome).astype(float)
        result.loc[group.index] = values.shift().expanding().mean().fillna(0.27)
    return result


def _team_prior_draw_rate(rows, side):
    result = pd.Series(0.27, index=rows.index, dtype=float)
    histories = {}
    for index, row in rows.sort_values("match_date").iterrows():
        key = (row["competition"], row[side])
        prior = histories.get(key, [])
        result.loc[index] = float(np.mean(prior)) if prior else 0.27
        histories.setdefault(key, []).append(row["actual_result"] == "DRAW")
    return result


def _class_recall(target, predicted, value):
    mask = target == value
    return float(np.mean(predicted[mask] == value)) if mask.any() else 0.0


def _contribution_table(rows, group):
    return rows.groupby(group).agg(newly_corrected=("newly_corrected", "sum"), newly_broken=("newly_broken", "sum")).reset_index().assign(net_corrected=lambda x: x.newly_corrected - x.newly_broken)


def _confusion(predictions):
    predicted = OUTCOMES[predictions[["challenger_home_probability", "challenger_draw_probability", "challenger_away_probability"]].to_numpy().argmax(axis=1)]
    return pd.crosstab(predictions["actual_result"], predicted, rownames=["actual"], colnames=["predicted"]).reindex(index=OUTCOMES, columns=OUTCOMES, fill_value=0).stack().rename("count").reset_index()


def _calibration(predictions):
    records = []
    for outcome, column in zip(OUTCOMES, ["challenger_home_probability", "challenger_draw_probability", "challenger_away_probability"]):
        buckets = pd.cut(predictions[column], bins=np.linspace(0, 1, 11), include_lowest=True)
        for bucket, group in predictions.groupby(buckets, observed=True):
            records.append({"outcome": outcome, "bucket": str(bucket), "count": len(group), "mean_predicted": group[column].mean(), "actual_rate": group["actual_result"].eq(outcome).mean()})
    return pd.DataFrame(records)


def _report(summary):
    headings = [
        ("A. Goal and baseline", f"Shadow challenger versus {summary['baseline_model_name']}."),
        ("B. Data and holdouts", f"{summary['rows_loaded']} rows, {summary['outer_holdout_count']} outer holdouts."),
        ("C. Rating model", summary["best_rating_model"]), ("D. Draw model", "Binary DRAW versus NON_DRAW."),
        ("E. HOME versus AWAY model", "Trained only on non-draw training matches."),
        ("F. Cross-fitting audit", f"OOF leakage count: {summary['oof_leakage_count']}."),
        ("G. Meta model", summary["best_meta_model"]),
        ("H. Hit-rate comparison", f"Baseline {summary['baseline_hit_rate']:.4f}; challenger {summary['challenger_hit_rate']:.4f}; delta {summary['hit_rate_delta']:+.4f}."),
        ("I. Brier and log loss", f"Brier improvement {summary['brier_improvement']:+.6f}; log-loss improvement {summary['log_loss_improvement']:+.6f}."),
        ("J. Draw performance", f"Precision {summary['challenger_draw_precision']:.4f}; recall {summary['challenger_draw_recall']:.4f}; F1 {summary['challenger_draw_f1']:.4f}."),
        ("K. Corrected versus broken", f"{summary['newly_corrected_count']} corrected, {summary['newly_broken_count']} broken, net {summary['net_corrected_count']}."),
        ("L. Holdout robustness", f"Positive rate {summary['positive_holdout_rate']:.4f}; worst delta {summary['worst_holdout_hit_delta']:+.4f}."),
        ("M. Team and league dominance", f"Competition {summary['dominant_competition_share']:.4f}; team {summary['dominant_team_share']:.4f}."),
        ("N. Leakage audit", f"Post-match rows {summary['post_match_rows_used_count']}; invalid probabilities {summary['invalid_probability_count']}."),
        ("O. Recommendation", f"**{summary['recommendation']}**. No production model was changed."),
    ]
    lines = ["# v2.18.0 Hierarchical Winner Challenger", ""]
    for heading, body in headings:
        lines.extend([f"## {heading}", "", body, ""])
    return "\n".join(lines)


def _json_default(value):
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return str(value)
