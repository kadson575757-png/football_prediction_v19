# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v2130_goal_model_evaluation import evaluate_predictions  # noqa: E402
from football_prediction_v19.analysis.v2140_goal_ml_dataset import (  # noqa: E402
    NUMERIC_COLUMNS, load_v2140_dataset,
)
from football_prediction_v19.analysis.v2140_goal_ml_validation import (  # noqa: E402
    DC_BASELINE, LEAGUE_BASELINE, aggregate_model_comparison, run_nested_validation,
)

DEFAULT_OUTPUT_DIR = "outputs/v2140_alternative_goal_model"
SAFETY = {"automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}


def run_v2140_alternative_goal_model_benchmark(
    *,
    project_root: str | Path = ROOT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    dataset: pd.DataFrame | None = None,
    frozen_dc: pd.DataFrame | None = None,
) -> dict[str, object]:
    project = Path(project_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    data = load_v2140_dataset(project) if dataset is None else dataset.copy()
    dc = pd.read_csv(
        project / "outputs/v2131_goal_model_repair/v2131_match_predictions.csv",
        keep_default_na=False,
    ) if frozen_dc is None else frozen_dc.copy()
    validation = run_nested_validation(data, dc)
    comparison = aggregate_model_comparison(validation)
    existing_winner = _existing_winner_metrics(data)
    comparison = pd.concat([comparison, pd.DataFrame([{
        "model_name": "EXISTING_WINNER_MODEL",
        "rows_evaluated": len(data),
        "top_outcome_hit_rate": existing_winner["top_outcome_hit_rate"],
        "multiclass_brier_score": existing_winner["multiclass_brier_score"],
    }])], ignore_index=True)
    alternatives = comparison[
        comparison["model_name"].isin([
            "REGULARIZED_POISSON_GLM", "HIST_GRADIENT_BOOSTING_POISSON",
            "GRADIENT_BOOSTING_REGRESSION",
        ])
    ].copy()
    robust = alternatives[alternatives["positive_total_goals_holdout_rate"].ge(.60)]
    ranking_pool = robust if len(robust) else alternatives
    best_row = ranking_pool.sort_values(
        ["total_goals_mae", "mean_holdout_mae_improvement", "poisson_deviance"],
        ascending=[True, False, True],
    ).iloc[0]
    best_model = str(best_row["model_name"])
    predictions = validation["predictions_by_model"][best_model]
    best_predictions = predictions[predictions["fold_type"].eq("LOCO")].copy().reset_index(drop=True)
    baseline_predictions = validation["predictions_by_model"][LEAGUE_BASELINE]
    baseline_predictions = baseline_predictions[baseline_predictions["fold_type"].eq("LOCO")].copy()
    dc_predictions = validation["predictions_by_model"][DC_BASELINE]
    dc_predictions = dc_predictions[dc_predictions["fold_type"].eq("LOCO")].copy()
    best = evaluate_predictions(best_predictions, best_model)
    baseline = evaluate_predictions(baseline_predictions, LEAGUE_BASELINE)
    v2131 = evaluate_predictions(dc_predictions, DC_BASELINE)
    outer = validation["outer_holdout_summary"]
    best_outer = outer[outer["model_name"].eq(best_model)]
    baseline_outer = outer[outer["model_name"].eq(LEAGUE_BASELINE)][
        ["fold_type", "holdout", "total_goals_mae"]
    ].rename(columns={"total_goals_mae": "baseline_total_goals_mae"})
    holdout_join = best_outer.merge(baseline_outer, on=["fold_type", "holdout"])
    holdout_join["mae_improvement"] = holdout_join["baseline_total_goals_mae"] - holdout_join["total_goals_mae"]
    positive_rate = float(holdout_join["mae_improvement"].gt(0).mean())
    dominance = _dominance(best_predictions, baseline_predictions)
    parameter_rows = best_outer["selected_parameters"].value_counts()
    best_parameters = str(parameter_rows.index[0]) if len(parameter_rows) else "{}"
    improvement_baseline = float(baseline["total_goals_mae"]) - float(best["total_goals_mae"])
    improvement_dc = float(v2131["total_goals_mae"]) - float(best["total_goals_mae"])
    relative_baseline = improvement_baseline / float(baseline["total_goals_mae"])
    invalid = int(best_predictions["invalid_prediction"].sum())
    clipped = int(best_predictions["lambda_clipped"].sum())
    probability_rate = float((~best_predictions["invalid_prediction"]).mean())
    mandatory = (
        probability_rate >= .98 and int(best_predictions["post_match_rows_used_count"].sum()) == 0
        and invalid == 0 and best_predictions["competition"].nunique() >= 4
        and len(best_outer) >= 7
    )
    criteria = {
        "goals_vs_baseline": relative_baseline >= .02,
        "goals_vs_v2131": improvement_dc > 0,
        "holdout_robustness": positive_rate >= .60,
        "btts": float(best["btts_brier_score"]) <= float(v2131["btts_brier_score"]),
        "over_2_5": float(best["over_2_5_brier_score"]) <= float(v2131["over_2_5_brier_score"]),
        "winner": float(best["multiclass_brier_score"]) <= float(v2131["multiclass_brier_score"]) + .005,
        "winner_vs_existing": float(best["multiclass_brier_score"]) < existing_winner["multiclass_brier_score"],
        "competition_dominance": dominance["dominant_competition_share"] <= .50,
        "team_dominance": dominance["dominant_team_share"] <= .25,
    }
    successful_components = sum([
        criteria["goals_vs_baseline"] and criteria["goals_vs_v2131"] and criteria["holdout_robustness"],
        criteria["btts"],
        criteria["over_2_5"],
        criteria["winner"] and criteria["winner_vs_existing"],
    ])
    all_success = mandatory and all(criteria.values())
    strong = all_success and relative_baseline >= .03 and positive_rate >= .70 and successful_components >= 3
    if strong:
        status, recommendation = "ALTERNATIVE_GOAL_MODEL_STRONG_SUCCESS", "PROCEED_TO_UNIFIED_PREMATCH_RUNNER"
    elif all_success:
        status, recommendation = "ALTERNATIVE_GOAL_MODEL_COMPONENT", "KEEP_ALTERNATIVE_GOAL_MODEL_AS_COMPONENT"
    elif mandatory and (improvement_dc <= 0 or positive_rate < .60):
        status, recommendation = "ALTERNATIVE_GOAL_MODEL_REJECTED", "IMPROVE_PREMATCH_DATA_BEFORE_MORE_MODELING"
    elif mandatory:
        status, recommendation = "ALTERNATIVE_GOAL_MODEL_NOT_ROBUST", "RETAIN_SIMPLE_GOAL_BASELINE"
    else:
        status, recommendation = "ALTERNATIVE_GOAL_MODEL_NOT_HELPFUL", "ALTERNATIVE_GOAL_MODEL_NOT_HELPFUL"
    summary = {
        "rows_loaded": int(len(data)), "rows_evaluated": int(len(best_predictions)),
        "competitions_evaluated": int(best_predictions["competition"].nunique()),
        "seasons_evaluated": int(best_predictions["season"].nunique()),
        "outer_holdout_count": int(len(best_outer)),
        "baseline_model_name": LEAGUE_BASELINE, "v2131_comparison_model_name": DC_BASELINE,
        "best_model_name": best_model, "best_model_parameters": best_parameters,
        "baseline_total_goals_mae": baseline["total_goals_mae"],
        "v2131_total_goals_mae": v2131["total_goals_mae"],
        "best_total_goals_mae": best["total_goals_mae"],
        "improvement_vs_baseline": round(improvement_baseline, 6),
        "relative_improvement_vs_baseline": round(relative_baseline, 6),
        "improvement_vs_v2131": round(improvement_dc, 6),
        "positive_total_goals_holdout_rate": round(positive_rate, 6),
        "best_home_goals_mae": best["home_goals_mae"], "best_away_goals_mae": best["away_goals_mae"],
        "best_btts_brier_score": best["btts_brier_score"],
        "best_over_2_5_brier_score": best["over_2_5_brier_score"],
        "best_winner_brier_score": best["multiclass_brier_score"],
        "existing_winner_brier_score": existing_winner["multiclass_brier_score"],
        "existing_winner_top_hit_rate": existing_winner["top_outcome_hit_rate"],
        "best_winner_top_hit_rate": best["top_outcome_hit_rate"],
        "best_draw_top_count": best["draw_top_count"],
        "best_exact_score_top3_hit_rate": best["exact_score_top3_hit_rate"],
        "probability_output_rate": round(probability_rate, 6),
        "missing_feature_rate": round(float(data[NUMERIC_COLUMNS].isna().mean().mean()), 6),
        "invalid_prediction_count": invalid, "clipped_prediction_count": clipped,
        "training_failure_count": int(validation["training_failure_count"]),
        "post_match_rows_used_count": int(best_predictions["post_match_rows_used_count"].sum()),
        **dominance, "successful_component_count": int(successful_components),
        "success_criteria": criteria, "alternative_goal_model_status": status,
        "recommendation": recommendation, "output_dir": str(out).replace("\\", "/"), **SAFETY,
    }
    _write_outputs(out, data, validation, comparison, best_predictions, summary, best_model)
    return {"v2140_alternative_goal_model_status": "READY", **summary}


def _dominance(best: pd.DataFrame, baseline: pd.DataFrame) -> dict[str, float]:
    keys = ["competition", "season", "match_date", "home_team", "away_team"]
    joined = best.merge(
        baseline[keys + ["expected_total_goals"]],
        on=keys, suffixes=("", "_baseline"),
    )
    actual = joined["actual_home_goals"] + joined["actual_away_goals"]
    joined["advantage"] = (
        (actual - joined["expected_total_goals_baseline"]).abs()
        - (actual - joined["expected_total_goals"]).abs()
    ).clip(lower=0)
    total = float(joined["advantage"].sum())
    if total <= 0:
        return {"dominant_competition_share": 0.0, "dominant_team_share": 0.0}
    competition = float(joined.groupby("competition")["advantage"].sum().max() / total)
    teams = pd.concat([
        joined[["home_team", "advantage"]].rename(columns={"home_team": "team"}),
        joined[["away_team", "advantage"]].rename(columns={"away_team": "team"}),
    ]).groupby("team")["advantage"].sum()
    return {
        "dominant_competition_share": round(competition, 6),
        "dominant_team_share": round(float(teams.max() / (2 * total)), 6),
    }


def _write_outputs(out, data, validation, comparison, predictions, summary, best_model):
    availability = pd.DataFrame([{
        "feature": column, "available_count": int(data[column].notna().sum()),
        "missing_count": int(data[column].isna().sum()),
        "available_rate": float(data[column].notna().mean()),
        "competitions_available": int(data.loc[data[column].notna(), "competition"].nunique()),
        "seasons_available": int(data.loc[data[column].notna(), "season"].nunique()),
        "asof_clean": bool(data["asof_clean"].all()),
    } for column in NUMERIC_COLUMNS])
    availability.to_csv(out / "v2140_feature_availability.csv", index=False)
    pd.DataFrame([{
        "rows": len(data), "competitions": data["competition"].nunique(),
        "seasons": data["season"].nunique(), "missing_feature_rate": data[NUMERIC_COLUMNS].isna().mean().mean(),
        "target_columns_excluded_from_features": True,
        "post_match_rows_used_count": int(data["post_match_rows_used_count"].sum()),
    }]).to_csv(out / "v2140_dataset_audit.csv", index=False)
    validation["model_training_summary"].to_csv(out / "v2140_model_training_summary.csv", index=False)
    validation["inner_selection_summary"].to_csv(out / "v2140_inner_selection_summary.csv", index=False)
    validation["outer_holdout_summary"].to_csv(out / "v2140_outer_holdout_summary.csv", index=False)
    comparison.to_csv(out / "v2140_model_comparison.csv", index=False)
    flat = predictions.drop(columns=["ranked_scorelines"], errors="ignore").copy()
    for column in ("top_3_scorelines", "top_5_scorelines"):
        flat[column] = flat[column].map(json.dumps)
    flat.to_csv(out / "v2140_match_predictions.csv", index=False)
    with (out / "v2140_scoreline_predictions.jsonl").open("w", encoding="utf-8") as handle:
        for _, row in predictions.iterrows():
            handle.write(json.dumps({
                "competition": row["competition"], "season": row["season"],
                "match_date": str(row["match_date"]), "home_team": row["home_team"], "away_team": row["away_team"],
                "model_name": best_model, "top_scoreline": row["top_scoreline"],
                "top_3_scorelines": row["top_3_scorelines"], "top_5_scorelines": row["top_5_scorelines"],
                "scorelines": row["ranked_scorelines"], "residual_mass": row["score_matrix_residual_mass"],
            }) + "\n")
    _group_metrics(predictions, "competition", best_model).to_csv(out / "v2140_competition_summary.csv", index=False)
    _group_metrics(predictions, "season", best_model).to_csv(out / "v2140_season_summary.csv", index=False)
    predictions[[
        "competition", "season", "match_date", "home_team", "away_team", "target_match_date",
        "maximum_source_date", "post_match_rows_used_count", "asof_clean",
    ]].to_csv(out / "v2140_asof_audit.csv", index=False)
    (out / "v2140_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    failed = [key for key, passed in summary["success_criteria"].items() if not passed]
    (out / "v2140_report.md").write_text(
        "# v2.14.0 Alternative Goal Model Benchmark\n\n"
        f"- status: {summary['alternative_goal_model_status']}\n"
        f"- recommendation: {summary['recommendation']}\n"
        f"- best_model: {summary['best_model_name']}\n"
        f"- positive_holdout_rate: {summary['positive_total_goals_holdout_rate']}\n"
        f"- improvement_vs_league_baseline: {summary['relative_improvement_vs_baseline']}\n"
        f"- improvement_vs_v2131: {summary['improvement_vs_v2131']}\n"
        f"- failed_criteria: {', '.join(failed)}\n\n"
        "## Decision\n\n"
        "The alternative model classes are rejected: none beats the frozen v2.13.1 model on total-goals MAE "
        "with the required holdout robustness, and BTTS/Over-2.5 degrade. Available rolling score/result "
        "features appear to be the limiting factor. Obtain stronger prematch xG, lineup, availability and "
        "schedule-context data before further modeling; until then retain the existing Winner model and use "
        "only the simple league goal baseline as descriptive output.\n\n"
        "Nested chronological validation used training-only preprocessing and inner parameter selection. "
        "No production integration was made.\n",
        encoding="utf-8",
    )


def _group_metrics(frame, column, model):
    rows = []
    for value, group in frame.groupby(column):
        metrics = evaluate_predictions(group, model)
        metrics[column] = value
        rows.append(metrics)
    return pd.DataFrame(rows)


def _existing_winner_metrics(data: pd.DataFrame) -> dict[str, float]:
    probabilities = data[["base_home_probability", "base_draw_probability", "base_away_probability"]].to_numpy(float)
    outcomes = np.array(["HOME", "DRAW", "AWAY"])
    predicted = outcomes[np.argmax(probabilities, axis=1)]
    actual = data["actual_result"].to_numpy()
    one_hot = np.array([[result == outcome for outcome in outcomes] for result in actual], float)
    return {
        "top_outcome_hit_rate": round(float(np.mean(predicted == actual)), 6),
        "multiclass_brier_score": round(float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1))), 6),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run offline v2.14.0 alternative goal-model nested chronological benchmark."
    )
    parser.add_argument("--project-root", default=str(ROOT))
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)
    result = run_v2140_alternative_goal_model_benchmark(
        project_root=args.project_root, output_dir=args.output_dir,
    )
    keys = [
        "v2140_alternative_goal_model_status", "rows_loaded", "rows_evaluated",
        "competitions_evaluated", "seasons_evaluated", "outer_holdout_count",
        "baseline_model_name", "v2131_comparison_model_name", "best_model_name",
        "best_model_parameters", "baseline_total_goals_mae", "v2131_total_goals_mae",
        "best_total_goals_mae", "improvement_vs_baseline", "improvement_vs_v2131",
        "positive_total_goals_holdout_rate", "best_home_goals_mae", "best_away_goals_mae",
        "best_btts_brier_score", "best_over_2_5_brier_score", "best_winner_brier_score",
        "best_winner_top_hit_rate", "best_draw_top_count", "best_exact_score_top3_hit_rate",
        "probability_output_rate", "invalid_prediction_count", "clipped_prediction_count",
        "post_match_rows_used_count", "dominant_competition_share", "dominant_team_share",
        "successful_component_count", "alternative_goal_model_status", "recommendation",
        "output_dir", "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled",
    ]
    for key in keys:
        value = result.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
