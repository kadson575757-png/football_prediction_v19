# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v2130_goal_distribution import load_local_goal_results  # noqa: E402
from football_prediction_v19.analysis.v2130_goal_model_evaluation import evaluate_predictions  # noqa: E402
from football_prediction_v19.analysis.v2130_rolling_goal_features import build_rolling_goal_features  # noqa: E402
from football_prediction_v19.analysis.v2131_goal_model_failure_audit import (  # noqa: E402
    failure_audit,
    model_difference_audit,
    select_training_only_holdouts,
)
from football_prediction_v19.analysis.v2131_repaired_goal_models import (  # noqa: E402
    BASELINE,
    generate_repaired_predictions,
)

DEFAULT_OUTPUT_DIR = "outputs/v2131_goal_model_repair"
SAFETY = {"automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}


def run_v2131_goal_model_repair_and_revalidation(
    *, project_root: str | Path = ROOT, output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    matches: pd.DataFrame | None = None,
) -> dict[str, object]:
    project = Path(project_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    source = load_local_goal_results(project) if matches is None else matches
    features = build_rolling_goal_features(source)
    predictions = generate_repaired_predictions(features)
    audits = failure_audit(predictions)
    differences = model_difference_audit(predictions, BASELINE)
    holdouts = select_training_only_holdouts(predictions, BASELINE)
    selections = holdouts["selected_model_name"].value_counts()
    best_model = sorted(selections[selections.eq(selections.max())].index)[0]
    best_rows = predictions[predictions["model_name"].eq(best_model)].copy()
    baseline_rows = predictions[predictions["model_name"].eq(BASELINE)].copy()
    best = evaluate_predictions(best_rows, best_model)
    baseline = evaluate_predictions(baseline_rows, BASELINE)
    model_comparison = pd.DataFrame([
        evaluate_predictions(predictions, model) for model in predictions["model_name"].unique()
    ])
    positive_holdout_rate = float(holdouts["positive"].mean())
    advantage = _dominance(best_rows, baseline_rows)
    invalid_lambda_count = int((
        ~best_rows["expected_home_goals"].between(.15, 4.5)
        | ~best_rows["expected_away_goals"].between(.15, 4.5)
    ).sum())
    clipped = int((best_rows["lambda_home_clipped"] | best_rows["lambda_away_clipped"]).sum())
    fallback_rate = float(best_rows["fallback_reason"].ne("").mean())
    mae_improvement = float(baseline["total_goals_mae"]) - float(best["total_goals_mae"])
    relative_improvement = mae_improvement / float(baseline["total_goals_mae"])
    mandatory = (
        float(best["probability_output_rate"]) >= .95 and invalid_lambda_count == 0
        and int(best_rows["post_match_rows_used_count"].sum()) == 0
        and best_rows["probability_valid"].all() and best_rows["competition"].nunique() >= 3
    )
    team_success = (
        best_model != BASELINE and relative_improvement >= .02 and positive_holdout_rate >= .60
        and float(best["btts_brier_score"]) <= float(baseline["btts_brier_score"])
        and float(best["over_2_5_brier_score"]) <= float(baseline["over_2_5_brier_score"])
        and advantage["dominant_competition_share"] <= .50 and advantage["dominant_team_share"] <= .25
    )
    rejection_required = (
        best_model == BASELINE
        or relative_improvement < .02
        or positive_holdout_rate < .60
    )
    extras = sum([
        float(best["multiclass_brier_score"]) < float(baseline["multiclass_brier_score"]),
        int(best["draw_top_count"]) > 0,
        float(best["exact_score_top3_hit_rate"]) > float(baseline["exact_score_top3_hit_rate"]),
    ])
    if mandatory and team_success:
        status, recommendation = "REPAIRED_GOAL_MODEL_SUCCESSFUL", "PROCEED_TO_UNIFIED_PREMATCH_RUNNER"
    elif mandatory and rejection_required:
        status, recommendation = "TEAM_POISSON_MODEL_REJECTED", "SWITCH_TO_ALTERNATIVE_GOAL_MODEL_CLASS"
    elif mandatory and best_model != BASELINE and (relative_improvement > 0 or extras):
        status, recommendation = "REPAIRED_GOAL_MODEL_COMPONENT_ONLY", "KEEP_REPAIRED_GOAL_MODEL_AS_COMPONENT"
    elif mandatory:
        status, recommendation = "TEAM_POISSON_MODEL_REJECTED", "SWITCH_TO_ALTERNATIVE_GOAL_MODEL_CLASS"
    else:
        status, recommendation = "GOAL_MODEL_NOT_HELPFUL", "GOAL_MODEL_NOT_HELPFUL"
    summary = {
        "rows_loaded": int(len(features)), "rows_evaluated": int(len(best_rows)),
        "competitions_evaluated": int(best_rows["competition"].nunique()),
        "seasons_evaluated": int(best_rows["season"].nunique()),
        "baseline_model_name": BASELINE, "best_model_name": best_model,
        "baseline_total_goals_mae": baseline["total_goals_mae"], "best_total_goals_mae": best["total_goals_mae"],
        "total_goals_mae_improvement": round(mae_improvement, 6),
        "relative_total_goals_mae_improvement": round(relative_improvement, 6),
        "baseline_btts_brier_score": baseline["btts_brier_score"], "best_btts_brier_score": best["btts_brier_score"],
        "baseline_over_2_5_brier_score": baseline["over_2_5_brier_score"], "best_over_2_5_brier_score": best["over_2_5_brier_score"],
        "baseline_winner_brier_score": baseline["multiclass_brier_score"], "best_winner_brier_score": best["multiclass_brier_score"],
        "best_winner_top_hit_rate": best["top_outcome_hit_rate"], "best_draw_top_count": best["draw_top_count"],
        "best_exact_score_top3_hit_rate": best["exact_score_top3_hit_rate"],
        "fallback_rate": round(fallback_rate, 6), "positive_holdout_rate": round(positive_holdout_rate, 6),
        "invalid_lambda_count": invalid_lambda_count, "clipped_lambda_count": clipped,
        "post_match_rows_used_count": int(best_rows["post_match_rows_used_count"].sum()),
        **advantage, "successful_component_count": int(team_success) + extras,
        "goal_model_status": status, "recommendation": recommendation,
        "output_dir": str(out).replace("\\", "/"), **SAFETY,
    }
    _write_outputs(out, best_rows, model_comparison, holdouts, audits, differences, summary, best_model)
    return {"v2131_goal_model_repair_status": "READY", **summary}


def _dominance(best: pd.DataFrame, baseline: pd.DataFrame) -> dict[str, float]:
    keys = ["competition", "season", "match_date", "home_team", "away_team"]
    joined = best.merge(
        baseline[keys + ["expected_total_goals"]], on=keys, suffixes=("", "_baseline")
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
    team = pd.concat([
        joined[["home_team", "advantage"]].rename(columns={"home_team": "team"}),
        joined[["away_team", "advantage"]].rename(columns={"away_team": "team"}),
    ]).groupby("team")["advantage"].sum()
    return {"dominant_competition_share": round(competition, 6), "dominant_team_share": round(float(team.max() / (2 * total)), 6)}


def _write_outputs(
    out: Path, best_rows: pd.DataFrame, comparison: pd.DataFrame, holdouts: pd.DataFrame,
    audits: pd.DataFrame, differences: pd.DataFrame, summary: dict[str, object], best_model: str,
) -> None:
    flat = best_rows.drop(columns=["ranked_scorelines"], errors="ignore").copy()
    for column in ("top_3_scorelines", "top_5_scorelines"):
        flat[column] = flat[column].map(json.dumps)
    flat.to_csv(out / "v2131_match_predictions.csv", index=False)
    audits.to_csv(out / "v2131_failure_audit.csv", index=False)
    best_rows.groupby(["home_feature_source", "away_feature_source", "fallback_reason"], dropna=False).size().reset_index(name="row_count").to_csv(out / "v2131_feature_source_audit.csv", index=False)
    audits[["model_name", "lambda_home_min", "lambda_home_max", "lambda_home_mean", "lambda_away_min", "lambda_away_max", "lambda_away_mean", "invalid_lambda_count", "clipped_lambda_count"]].to_csv(out / "v2131_lambda_audit.csv", index=False)
    differences.to_csv(out / "v2131_model_difference_audit.csv", index=False)
    comparison.to_csv(out / "v2131_model_comparison.csv", index=False)
    holdouts.to_csv(out / "v2131_holdout_summary.csv", index=False)
    _groups(best_rows, "competition", best_model).to_csv(out / "v2131_competition_summary.csv", index=False)
    _groups(best_rows, "season", best_model).to_csv(out / "v2131_season_summary.csv", index=False)
    best_rows[["competition", "season", "match_date", "home_team", "away_team", "target_match_date", "maximum_source_date", "post_match_rows_used_count", "asof_clean"]].to_csv(out / "v2131_asof_audit.csv", index=False)
    (out / "v2131_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out / "v2131_report.md").write_text(
        "# v2.13.1 Goal Model Repair and Revalidation\n\n"
        f"- status: {summary['goal_model_status']}\n- recommendation: {summary['recommendation']}\n"
        f"- best_model: {summary['best_model_name']}\n- positive_holdout_rate: {summary['positive_holdout_rate']}\n\n"
        "All selection parameters were chosen on training folds only. No production integration was made.\n",
        encoding="utf-8",
    )


def _groups(frame: pd.DataFrame, column: str, model: str) -> pd.DataFrame:
    rows = []
    for value, group in frame.groupby(column):
        metric = evaluate_predictions(group, model)
        metric[column] = value
        rows.append(metric)
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=str(ROOT))
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)
    result = run_v2131_goal_model_repair_and_revalidation(project_root=args.project_root, output_dir=args.output_dir)
    keys = [
        "v2131_goal_model_repair_status", "rows_loaded", "rows_evaluated", "competitions_evaluated", "seasons_evaluated",
        "baseline_model_name", "best_model_name", "baseline_total_goals_mae", "best_total_goals_mae",
        "total_goals_mae_improvement", "baseline_btts_brier_score", "best_btts_brier_score",
        "baseline_over_2_5_brier_score", "best_over_2_5_brier_score", "baseline_winner_brier_score",
        "best_winner_brier_score", "best_winner_top_hit_rate", "best_draw_top_count",
        "best_exact_score_top3_hit_rate", "fallback_rate", "positive_holdout_rate", "invalid_lambda_count",
        "clipped_lambda_count", "post_match_rows_used_count", "dominant_competition_share", "dominant_team_share",
        "successful_component_count", "goal_model_status", "recommendation", "output_dir",
        "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled",
    ]
    for key in keys:
        value = result.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
