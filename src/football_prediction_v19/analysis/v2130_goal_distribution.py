# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from football_prediction_v19.analysis.v2130_goal_model_evaluation import (
    build_holdout_summary,
    evaluate_predictions,
)
from football_prediction_v19.analysis.v2130_match_profile import derive_match_profile
from football_prediction_v19.analysis.v2130_poisson_models import MODEL_NAMES, expected_goals_for_model
from football_prediction_v19.analysis.v2130_rolling_goal_features import build_rolling_goal_features, prepare_matches
from football_prediction_v19.analysis.v2130_score_matrix import build_score_matrix, derive_distribution


SAFETY_FLAGS = {
    "automatic_betting_enabled": False,
    "staking_logic_enabled": False,
    "roi_logic_enabled": False,
}
DEFAULT_OUTPUT_DIR = "outputs/v2130_unified_goal_distribution"


def load_local_goal_results(root: str | Path = ".") -> pd.DataFrame:
    root_path = Path(root)
    paths = [
        root_path / "outputs/v2124_pl_multi_season_robustness/season_runs/2023_24/fixture_load/fixture_catalog/season_fixture_catalog.csv",
        root_path / "outputs/v2124_pl_multi_season_robustness/season_runs/2024_25/fixture_load/fixture_catalog/season_fixture_catalog.csv",
        root_path / "outputs/premier_league_2025_26_full_analysis/fixture_catalog/season_fixture_catalog.csv",
    ]
    for competition in ("bundesliga", "la_liga", "serie_a"):
        for season in ("2023_24", "2024_25", "2025_26"):
            paths.append(
                root_path / f"outputs/v2126_external_league_edge_calibration/competition_runs/{competition}/{season}/fixture_load/season_fixture_catalog.csv"
            )
    frames = [pd.read_csv(path, keep_default_na=False) for path in paths if path.exists()]
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.rename(columns={"home_goals": "actual_home_goals", "away_goals": "actual_away_goals"})
    return prepare_matches(combined).drop_duplicates(
        ["competition", "season", "match_date", "home_team", "away_team"], keep="last"
    )


def generate_candidate_predictions(feature_rows: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for _, feature in feature_rows.iterrows():
        for model_name in MODEL_NAMES:
            home_xg, away_xg, rho = expected_goals_for_model(feature, model_name)
            matrix_max = 8
            matrix, residual = build_score_matrix(home_xg, away_xg, max_goals=matrix_max, rho=rho)
            while residual >= 1e-6 and matrix_max < 20:
                matrix_max += 2
                matrix, residual = build_score_matrix(home_xg, away_xg, max_goals=matrix_max, rho=rho)
            distribution = derive_distribution(matrix)
            record = feature.to_dict()
            record.update(distribution)
            record.update({
                "model_name": model_name,
                "expected_home_goals": home_xg,
                "expected_away_goals": away_xg,
                "expected_total_goals": home_xg + away_xg,
                "dixon_coles_rho": rho,
                "matrix_max_goals": matrix_max,
                "score_matrix_residual_mass": residual,
                "probability_valid": _probability_valid(distribution, residual),
                "match_profile": derive_match_profile(distribution, home_xg, away_xg),
            })
            records.append(record)
    return pd.DataFrame(records)


def analyze_unified_goal_distribution(
    matches: pd.DataFrame,
    *,
    existing_winner_rows: pd.DataFrame | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    prepared = prepare_matches(matches)
    features = build_rolling_goal_features(prepared)
    candidates = generate_candidate_predictions(features)
    holdouts, best_model = build_holdout_summary(candidates)
    selected = candidates[candidates["model_name"].eq(best_model)].copy().reset_index(drop=True)
    comparison = pd.DataFrame([evaluate_predictions(candidates, name) for name in MODEL_NAMES])
    selected_metrics = evaluate_predictions(selected, best_model)
    baseline_metrics = evaluate_predictions(candidates, "ROLLING_LEAGUE_MEAN_POISSON")
    existing_metrics = _existing_winner_metrics(existing_winner_rows)
    competition_summary = _group_metrics(selected, "competition", best_model)
    season_summary = _group_metrics(selected, "season", best_model)
    asof = selected[[
        "competition", "season", "match_date", "home_team", "away_team", "target_match_date",
        "maximum_source_date", "post_match_rows_used_count", "asof_clean",
    ]].copy()
    availability = _feature_availability(features)
    positive_holdout_rate = float(holdouts["positive"].mean()) if len(holdouts) else 0.0
    component_flags = _component_success(selected_metrics, baseline_metrics, existing_metrics, positive_holdout_rate)
    successful_components = sum(component_flags.values())
    mandatory = bool(
        float(selected_metrics["probability_output_rate"]) >= 0.95
        and int(asof["post_match_rows_used_count"].sum()) == 0
        and selected["probability_valid"].all()
        and selected["competition"].nunique() >= 3
    )
    if mandatory and successful_components >= 3:
        goal_status, recommendation = "GOAL_DISTRIBUTION_SUCCESSFUL", "PROCEED_TO_UNIFIED_PREMATCH_RUNNER"
    elif mandatory and successful_components >= 1:
        goal_status, recommendation = "GOAL_DISTRIBUTION_COMPONENT_ONLY", "KEEP_GOAL_MODEL_AS_COMPONENT"
    elif mandatory:
        goal_status, recommendation = "GOAL_DISTRIBUTION_REQUIRES_REVISION", "GOAL_MODEL_REQUIRES_REVISION"
    else:
        goal_status, recommendation = "GOAL_DISTRIBUTION_NOT_HELPFUL", "GOAL_MODEL_NOT_HELPFUL"
    summary = {
        "rows_loaded": int(len(prepared)),
        "rows_evaluated": int(len(selected)),
        "competitions_evaluated": int(selected["competition"].nunique()),
        "seasons_evaluated": int(selected["season"].nunique()),
        "probability_output_rate": selected_metrics["probability_output_rate"],
        "best_model_name": best_model,
        "home_goals_mae": selected_metrics["home_goals_mae"],
        "away_goals_mae": selected_metrics["away_goals_mae"],
        "total_goals_mae": selected_metrics["total_goals_mae"],
        "winner_top_hit_rate": selected_metrics["top_outcome_hit_rate"],
        "winner_brier_score": selected_metrics["multiclass_brier_score"],
        "draw_top_count": selected_metrics["draw_top_count"],
        "draw_top_hit_rate": selected_metrics["draw_top_hit_rate"],
        "btts_brier_score": selected_metrics["btts_brier_score"],
        "btts_f1": selected_metrics["btts_f1"],
        "over_2_5_brier_score": selected_metrics["over_2_5_brier_score"],
        "goal_bucket_hit_rate": selected_metrics["goal_bucket_hit_rate"],
        "exact_score_top1_hit_rate": selected_metrics["exact_score_top1_hit_rate"],
        "exact_score_top3_hit_rate": selected_metrics["exact_score_top3_hit_rate"],
        "exact_score_top5_hit_rate": selected_metrics["exact_score_top5_hit_rate"],
        "positive_holdout_rate": round(positive_holdout_rate, 6),
        "post_match_rows_used_count": int(asof["post_match_rows_used_count"].sum()),
        "invalid_probability_count": int((~selected["probability_valid"]).sum()),
        "maximum_probability_sum_error": float((selected["probability_sum"] - 1.0).abs().max()) if len(selected) else 0.0,
        "maximum_score_matrix_residual_mass": float(selected["score_matrix_residual_mass"].max()) if len(selected) else 0.0,
        "existing_winner_brier_score": existing_metrics.get("multiclass_brier_score"),
        "successful_component_count": int(successful_components),
        "successful_components": component_flags,
        "goal_distribution_status": goal_status,
        "recommendation": recommendation,
        "output_dir": str(out).replace("\\", "/"),
        **SAFETY_FLAGS,
    }
    _write_outputs(out, selected, comparison, holdouts, competition_summary, season_summary, asof, availability, summary)
    return {"v2130_unified_goal_distribution_status": "READY", **summary}


def _write_outputs(
    out: Path, selected: pd.DataFrame, comparison: pd.DataFrame, holdouts: pd.DataFrame,
    competition_summary: pd.DataFrame, season_summary: pd.DataFrame, asof: pd.DataFrame,
    availability: pd.DataFrame, summary: dict[str, object],
) -> None:
    non_nested = selected.drop(columns=["ranked_scorelines"], errors="ignore").copy()
    for column in ("top_3_scorelines", "top_5_scorelines"):
        non_nested[column] = non_nested[column].map(json.dumps)
    non_nested.to_csv(out / "v2130_match_predictions.csv", index=False)
    with (out / "v2130_scoreline_predictions.jsonl").open("w", encoding="utf-8") as handle:
        for _, row in selected.iterrows():
            payload = {
                "competition": row["competition"], "season": row["season"],
                "match_date": str(row["match_date"]), "home_team": row["home_team"], "away_team": row["away_team"],
                "matrix_max_goals": int(row["matrix_max_goals"]),
                "residual_probability": float(row["score_matrix_residual_mass"]),
                "scorelines": row["ranked_scorelines"],
            }
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    availability.to_csv(out / "v2130_feature_availability.csv", index=False)
    comparison.to_csv(out / "v2130_model_comparison.csv", index=False)
    holdouts.to_csv(out / "v2130_holdout_summary.csv", index=False)
    competition_summary.to_csv(out / "v2130_competition_summary.csv", index=False)
    season_summary.to_csv(out / "v2130_season_summary.csv", index=False)
    asof.to_csv(out / "v2130_asof_audit.csv", index=False)
    (out / "v2130_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "v2130_report.md").write_text(_render_report(summary, comparison, holdouts), encoding="utf-8")


def _feature_availability(features: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "league_home_goals_mean", "league_away_goals_mean", "home_attack_strength",
        "home_defense_strength", "away_attack_strength", "away_defense_strength",
        "home_form5_attack_factor", "away_form5_attack_factor", "home_venue_attack_strength",
        "away_venue_attack_strength",
    ]
    return pd.DataFrame([{
        "feature": column,
        "available_count": int(features[column].notna().sum()),
        "missing_count": int(features[column].isna().sum()),
        "available_rate": round(float(features[column].notna().mean()), 6),
        "competitions_available": int(features.loc[features[column].notna(), "competition"].nunique()),
        "seasons_available": int(features.loc[features[column].notna(), "season"].nunique()),
        "asof_clean": bool(features["asof_clean"].all()),
    } for column in columns])


def _group_metrics(selected: pd.DataFrame, column: str, model_name: str) -> pd.DataFrame:
    rows = []
    for value, group in selected.groupby(column):
        metric = evaluate_predictions(group, model_name)
        metric[column] = value
        rows.append(metric)
    return pd.DataFrame(rows)


def _existing_winner_metrics(rows: pd.DataFrame | None) -> dict[str, float]:
    if rows is None or rows.empty:
        return {}
    required = {"actual_result", "home_win_probability", "draw_probability", "away_win_probability"}
    if not required.issubset(rows.columns):
        return {}
    valid = rows[rows["actual_result"].isin(["HOME", "DRAW", "AWAY"])]
    probs = valid[["home_win_probability", "draw_probability", "away_win_probability"]].astype(float).to_numpy()
    actual = np.array([[result == outcome for outcome in ("HOME", "DRAW", "AWAY")] for result in valid["actual_result"]], float)
    return {"multiclass_brier_score": round(float(np.mean(np.sum((probs - actual) ** 2, axis=1))), 6)}


def _component_success(
    selected: dict[str, object], baseline: dict[str, object], existing: dict[str, float], positive_rate: float,
) -> dict[str, bool]:
    goal = float(selected["total_goals_mae"]) <= float(baseline["total_goals_mae"]) * 0.97 and positive_rate >= 0.6
    winner = bool(existing) and float(selected["multiclass_brier_score"]) < float(existing["multiclass_brier_score"])
    btts = float(selected["btts_brier_score"]) < float(baseline["btts_brier_score"]) and positive_rate >= 0.6
    totals = sum(
        float(selected[f"over_{line}_brier_score"]) < float(baseline[f"over_{line}_brier_score"])
        for line in ("1_5", "2_5", "3_5")
    ) >= 2
    scorelines = (
        float(selected["exact_score_top3_hit_rate"]) > float(baseline["exact_score_top3_hit_rate"])
        and float(selected["exact_score_top5_hit_rate"]) > float(baseline["exact_score_top5_hit_rate"])
        and positive_rate >= 0.6
    )
    return {"goals": goal, "winner": winner, "btts": btts, "totals": totals, "scorelines": scorelines}


def _probability_valid(distribution: dict[str, object], residual: float) -> bool:
    fields = [
        "home_win_probability", "draw_probability", "away_win_probability",
        "btts_yes_probability", "btts_no_probability", "total_goals_0_1_probability",
        "total_goals_2_3_probability", "total_goals_4_plus_probability",
        "over_1_5_probability", "under_1_5_probability", "over_2_5_probability",
        "under_2_5_probability", "over_3_5_probability", "under_3_5_probability",
    ]
    values = [float(distribution[field]) for field in fields]
    return (
        all(np.isfinite(value) and 0 <= value <= 1 for value in values)
        and abs(float(distribution["probability_sum"]) - 1.0) <= 1e-12
        and residual < 1e-6
    )


def _render_report(summary: dict[str, object], comparison: pd.DataFrame, holdouts: pd.DataFrame) -> str:
    return "\n".join([
        "# v2.13.0 Unified Goal Distribution Model Foundation", "",
        "## Summary", "",
        f"- best_model_name: {summary['best_model_name']}",
        f"- goal_distribution_status: {summary['goal_distribution_status']}",
        f"- recommendation: {summary['recommendation']}",
        f"- successful_component_count: {summary['successful_component_count']}",
        f"- post_match_rows_used_count: {summary['post_match_rows_used_count']}", "",
        "## Model comparison", "", _markdown_table(comparison), "",
        "## Training-only holdouts", "", _markdown_table(holdouts), "",
        "No production model change was made. HIGH_EDGE_SHARPEN_005 was not integrated.",
        "Safety: automatic_betting_enabled=false, staking_logic_enabled=false, roi_logic_enabled=false.",
    ])


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return ""
    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row[column]) for column in columns) + " |")
    return "\n".join(lines)
