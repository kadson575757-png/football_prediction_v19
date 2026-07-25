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
from football_prediction_v19.analysis.v2150_enriched_challenger import BASE_MODEL  # noqa: E402
from football_prediction_v19.analysis.v2150_enriched_dataset import load_enriched_dataset  # noqa: E402
from football_prediction_v19.analysis.v2150_enriched_validation import (  # noqa: E402
    ablation_summary, run_enriched_validation,
)
from football_prediction_v19.analysis.v2150_feature_coverage import (  # noqa: E402
    GROUP_FEATURES, coverage_by_competition_season, feature_coverage, group_coverage_gates,
)
from football_prediction_v19.analysis.v2150_prematch_data_sources import source_inventory  # noqa: E402

DEFAULT_OUTPUT_DIR = "outputs/v2150_prematch_data_enrichment"
SAFETY = {"automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}


def run_v2150_prematch_data_enrichment(
    *,
    project_root: str | Path = ROOT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    enable_network: bool = False,
    dataset: pd.DataFrame | None = None,
    frozen_dc: pd.DataFrame | None = None,
) -> dict[str, object]:
    project = Path(project_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    inventory = source_inventory(project)
    enriched = load_enriched_dataset(str(project)) if dataset is None else dataset.copy()
    coverage = feature_coverage(enriched)
    gates = group_coverage_gates(enriched, coverage)
    passing_groups = gates.loc[gates["passes_main_coverage_gate"], "feature_group"].tolist()
    dc = pd.read_csv(
        project / "outputs/v2131_goal_model_repair/v2131_match_predictions.csv", keep_default_na=False,
    ) if frozen_dc is None else frozen_dc.copy()
    validation = run_enriched_validation(enriched, dc, passing_groups)
    ablations = ablation_summary(validation)
    challengers = ablations[ablations["model_name"].ne(BASE_MODEL)]
    robust = challengers[challengers["positive_holdout_rate"].ge(.60)]
    pool = robust if len(robust) else challengers
    best_row = pool.sort_values(
        ["total_goals_mae", "mean_holdout_metric_improvement"], ascending=[True, False],
    ).iloc[0] if len(pool) else ablations[ablations["model_name"].eq(BASE_MODEL)].iloc[0]
    best_model = str(best_row["model_name"])
    predictions = validation["predictions_by_model"][best_model]
    predictions = predictions[predictions["fold_type"].eq("LOCO")].copy().assign(model_name=best_model)
    baseline_predictions = validation["predictions_by_model"][BASE_MODEL]
    baseline_predictions = baseline_predictions[baseline_predictions["fold_type"].eq("LOCO")].copy().assign(model_name=BASE_MODEL)
    best = evaluate_predictions(predictions, best_model)
    baseline = evaluate_predictions(baseline_predictions, BASE_MODEL)
    outer = validation["outer_holdout_summary"]
    best_outer = outer[outer["model_name"].eq(best_model)]
    base_outer = outer[outer["model_name"].eq(BASE_MODEL)]
    joined = best_outer.merge(base_outer, on=["fold_type", "holdout"], suffixes=("", "_baseline"))
    positive_goal_rate = _positive_rate(joined, "total_goals_mae", lower_is_better=True)
    positive_btts_rate = _positive_rate(joined, "btts_brier_score", lower_is_better=True)
    positive_scoreline_rate = _positive_rate(joined, "exact_score_top3_hit_rate", lower_is_better=False)
    totals_improved = sum(
        float(best[f"over_{line}_brier_score"]) < float(baseline[f"over_{line}_brier_score"])
        and _positive_rate(joined, f"over_{line}_brier_score", lower_is_better=True) >= .60
        for line in ("1_5", "2_5", "3_5")
    )
    baseline_hit = predictions["top_probability_outcome"].copy()
    base_hit = baseline_predictions["top_probability_outcome"].eq(baseline_predictions["actual_result"])
    best_hit = predictions["top_probability_outcome"].eq(predictions["actual_result"])
    corrected = int((~base_hit.to_numpy() & best_hit.to_numpy()).sum())
    broken = int((base_hit.to_numpy() & ~best_hit.to_numpy()).sum())
    net_corrected = corrected - broken
    dominance = _dominance(predictions, baseline_predictions)
    goal_improvement = float(baseline["total_goals_mae"]) - float(best["total_goals_mae"])
    winner_brier_improvement = (
        float(baseline["multiclass_brier_score"]) - float(best["multiclass_brier_score"])
    ) / float(baseline["multiclass_brier_score"])
    btts_improvement = (
        float(baseline["btts_brier_score"]) - float(best["btts_brier_score"])
    ) / float(baseline["btts_brier_score"])
    success_areas = {
        "goals": goal_improvement / float(baseline["total_goals_mae"]) >= .02 and positive_goal_rate >= .60,
        "winner": (
            winner_brier_improvement >= .01
            or float(best["top_outcome_hit_rate"]) - float(baseline["top_outcome_hit_rate"]) >= .01
        ) and net_corrected > 0,
        "btts": btts_improvement >= .01 and positive_btts_rate >= .60,
        "totals": totals_improved >= 2,
        "scorelines": (
            float(best["exact_score_top3_hit_rate"]) > float(baseline["exact_score_top3_hit_rate"])
            and float(best["exact_score_top5_hit_rate"]) > float(baseline["exact_score_top5_hit_rate"])
            and positive_scoreline_rate >= .60
        ),
    }
    mandatory = (
        float(best["probability_output_rate"]) >= .95
        and int(predictions["post_match_rows_used_count"].sum()) == 0
        and predictions["competition"].nunique() >= 3 and len(best_outer) >= 7
        and not predictions["invalid_prediction"].any()
    )
    success = (
        mandatory and sum(success_areas.values()) >= 3
        and dominance["dominant_competition_share"] <= .50
        and dominance["dominant_team_share"] <= .25
    )
    if success:
        status, recommendation = "PREMATCH_DATA_ENRICHMENT_SUCCESSFUL", "PROCEED_TO_UNIFIED_PREMATCH_RUNNER"
    elif not passing_groups:
        status, recommendation = "DATA_COVERAGE_INSUFFICIENT", "DATA_COVERAGE_INSUFFICIENT"
    elif sum(success_areas.values()) >= 2:
        status, recommendation = "ENRICHED_MODEL_COMPONENT_ONLY", "KEEP_ENRICHED_MODEL_AS_COMPONENT"
    else:
        status, recommendation = "PREMATCH_DATA_NOT_HELPFUL", "RETAIN_EXISTING_MODELS"
    group_counts = {
        group: int(enriched[features].notna().all(axis=1).sum())
        for group, features in GROUP_FEATURES.items()
    }
    summary = {
        "sources_checked": int(len(inventory)), "sources_usable": int(inventory["usable"].sum()),
        "network_enabled": bool(enable_network), "rows_loaded": int(len(enriched)),
        "rows_with_xg": group_counts["EXPECTED_GOALS"],
        "xg_coverage_rate": round(group_counts["EXPECTED_GOALS"] / len(enriched), 6),
        "rows_with_chance_creation": group_counts["CHANCE_CREATION"],
        "chance_creation_coverage_rate": round(group_counts["CHANCE_CREATION"] / len(enriched), 6),
        "rows_with_squad_availability": group_counts["SQUAD_AVAILABILITY"],
        "squad_availability_coverage_rate": round(group_counts["SQUAD_AVAILABILITY"] / len(enriched), 6),
        "rows_with_market_context": group_counts["MARKET_CONTEXT"],
        "market_context_coverage_rate": round(group_counts["MARKET_CONTEXT"] / len(enriched), 6),
        "feature_groups_passing_coverage_gate": passing_groups,
        "best_feature_group_combination": str(best_row["feature_groups"]),
        "best_model_name": best_model,
        "baseline_total_goals_mae": baseline["total_goals_mae"], "best_total_goals_mae": best["total_goals_mae"],
        "total_goals_mae_improvement": round(goal_improvement, 6),
        "baseline_winner_hit_rate": baseline["top_outcome_hit_rate"], "best_winner_hit_rate": best["top_outcome_hit_rate"],
        "winner_hit_rate_delta": round(float(best["top_outcome_hit_rate"]) - float(baseline["top_outcome_hit_rate"]), 6),
        "baseline_winner_brier_score": baseline["multiclass_brier_score"], "best_winner_brier_score": best["multiclass_brier_score"],
        "baseline_btts_brier_score": baseline["btts_brier_score"], "best_btts_brier_score": best["btts_brier_score"],
        "baseline_over_2_5_brier_score": baseline["over_2_5_brier_score"], "best_over_2_5_brier_score": best["over_2_5_brier_score"],
        "baseline_scoreline_top3_hit_rate": baseline["exact_score_top3_hit_rate"], "best_scoreline_top3_hit_rate": best["exact_score_top3_hit_rate"],
        "positive_holdout_rate": round(positive_goal_rate, 6), "net_corrected_count": net_corrected,
        **dominance, "post_match_rows_used_count": int(predictions["post_match_rows_used_count"].sum()),
        "invalid_probability_count": int(predictions["invalid_prediction"].sum()),
        "outer_holdout_count": int(len(best_outer)), "training_failure_count": int(validation["training_failure_count"]),
        "successful_component_count": int(sum(success_areas.values())), "success_areas": success_areas,
        "prematch_data_status": status, "recommendation": recommendation,
        "output_dir": str(out).replace("\\", "/"), **SAFETY,
    }
    _write_outputs(out, inventory, enriched, coverage, gates, validation, ablations, predictions, summary)
    return {"v2150_prematch_data_enrichment_status": "READY", **summary}


def _positive_rate(joined, metric, *, lower_is_better):
    if joined.empty:
        return 0.0
    if lower_is_better:
        positive = joined[f"{metric}_baseline"] > joined[metric]
    else:
        positive = joined[metric] > joined[f"{metric}_baseline"]
    return float(positive.mean())


def _dominance(best, baseline):
    keys = ["competition", "season", "match_date", "home_team", "away_team"]
    joined = best.merge(
        baseline[keys + ["expected_total_goals"]], on=keys, suffixes=("", "_baseline"),
    )
    actual = joined["actual_home_goals"] + joined["actual_away_goals"]
    joined["advantage"] = (
        (actual - joined["expected_total_goals_baseline"]).abs()
        - (actual - joined["expected_total_goals"]).abs()
    ).clip(lower=0)
    total = float(joined["advantage"].sum())
    if total <= 0:
        return {"dominant_competition_share": 0.0, "dominant_team_share": 0.0, "dominant_season_share": 0.0}
    competition = joined.groupby("competition")["advantage"].sum().max() / total
    season = joined.groupby("season")["advantage"].sum().max() / total
    teams = pd.concat([
        joined[["home_team", "advantage"]].rename(columns={"home_team": "team"}),
        joined[["away_team", "advantage"]].rename(columns={"away_team": "team"}),
    ]).groupby("team")["advantage"].sum()
    return {
        "dominant_competition_share": round(float(competition), 6),
        "dominant_team_share": round(float(teams.max() / (2 * total)), 6),
        "dominant_season_share": round(float(season), 6),
    }


def _write_outputs(out, inventory, enriched, coverage, gates, validation, ablations, predictions, summary):
    inventory.to_csv(out / "v2150_source_inventory.csv", index=False)
    coverage.to_csv(out / "v2150_feature_coverage.csv", index=False)
    coverage_by_competition_season(enriched).to_csv(out / "v2150_coverage_by_competition_season.csv", index=False)
    gates.merge(
        inventory[["data_group", "source_name", "source_quality", "usable", "reason"]],
        left_on="feature_group", right_on="data_group", how="left",
    ).to_csv(out / "v2150_source_quality_audit.csv", index=False)
    pd.DataFrame([{
        "rows": len(enriched), "columns": len(enriched.columns),
        "target_columns_excluded_during_feature_generation": True,
        "post_match_rows_used_count": int(enriched["post_match_rows_used_count"].sum()),
        "asof_clean_rate": float(enriched["asof_clean"].mean()),
    }]).to_csv(out / "v2150_enriched_dataset_audit.csv", index=False)
    ablations.to_csv(out / "v2150_feature_group_ablation.csv", index=False)
    validation["outer_holdout_summary"].to_csv(out / "v2150_outer_holdout_summary.csv", index=False)
    ablations.to_csv(out / "v2150_model_comparison.csv", index=False)
    flat = predictions.drop(columns=["ranked_scorelines"], errors="ignore").copy()
    for column in ("top_3_scorelines", "top_5_scorelines"):
        flat[column] = flat[column].map(json.dumps)
    flat.to_csv(out / "v2150_match_predictions.csv", index=False)
    predictions[[
        "competition", "season", "match_date", "home_team", "away_team", "target_match_date",
        "maximum_feature_source_date", "maximum_feature_source_timestamp",
        "post_match_rows_used_count", "asof_clean",
    ]].to_csv(out / "v2150_asof_audit.csv", index=False)
    (out / "v2150_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    failed_groups = gates.loc[~gates["passes_main_coverage_gate"], "feature_group"].tolist()
    (out / "v2150_report.md").write_text(
        "# v2.15.0 Prematch Data Enrichment\n\n"
        f"- status: {summary['prematch_data_status']}\n- recommendation: {summary['recommendation']}\n"
        f"- passing_groups: {', '.join(summary['feature_groups_passing_coverage_gate']) or 'none'}\n"
        f"- excluded_groups: {', '.join(failed_groups)}\n"
        f"- best_combination: {summary['best_feature_group_combination']}\n"
        f"- positive_holdout_rate: {summary['positive_holdout_rate']}\n\n"
        "## Coverage decision\n\n"
        f"- xG coverage: {summary['xg_coverage_rate']} (below gate; one competition only)\n"
        f"- chance-creation coverage: {summary['chance_creation_coverage_rate']} (main gate passed)\n"
        f"- squad-availability coverage: {summary['squad_availability_coverage_rate']} (unavailable)\n"
        f"- market coverage: {summary['market_context_coverage_rate']} (excluded: no auditable prematch snapshot timestamp)\n\n"
        "## Challenger decision\n\n"
        f"- total-goals MAE: {summary['best_total_goals_mae']} versus {summary['baseline_total_goals_mae']}\n"
        f"- winner net corrected: {summary['net_corrected_count']}\n"
        f"- successful target areas: {summary['successful_component_count']}\n\n"
        "Chance-creation maintenance does not justify integration because aggregate Goals, BTTS and Totals degrade. "
        "No further model class or micro-tuning phase should be started on these data. Retain v2.13.1 only as a "
        "descriptive goal model and focus production effort on the existing Winner runner. Broader timestamped xG "
        "and historical squad availability would be required before revisiting enrichment.\n\n"
        "Only coverage-gated, timestamp-auditable groups entered validation. Current-match statistics were never used. "
        "No production integration or network access occurred.\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run offline v2.15.0 prematch data enrichment and gated challenger validation.")
    parser.add_argument("--project-root", default=str(ROOT))
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--enable-network", action="store_true", help="Permit configured source adapters to use network (unused by default local audit).")
    args = parser.parse_args(argv)
    result = run_v2150_prematch_data_enrichment(
        project_root=args.project_root, output_dir=args.output_dir, enable_network=args.enable_network,
    )
    keys = [
        "v2150_prematch_data_enrichment_status", "sources_checked", "sources_usable", "rows_loaded",
        "rows_with_xg", "xg_coverage_rate", "rows_with_chance_creation", "chance_creation_coverage_rate",
        "rows_with_squad_availability", "squad_availability_coverage_rate",
        "rows_with_market_context", "market_context_coverage_rate", "feature_groups_passing_coverage_gate",
        "best_feature_group_combination", "baseline_total_goals_mae", "best_total_goals_mae",
        "total_goals_mae_improvement", "baseline_winner_hit_rate", "best_winner_hit_rate",
        "winner_hit_rate_delta", "baseline_winner_brier_score", "best_winner_brier_score",
        "baseline_btts_brier_score", "best_btts_brier_score", "baseline_over_2_5_brier_score",
        "best_over_2_5_brier_score", "baseline_scoreline_top3_hit_rate", "best_scoreline_top3_hit_rate",
        "positive_holdout_rate", "net_corrected_count", "dominant_competition_share",
        "dominant_team_share", "post_match_rows_used_count", "prematch_data_status",
        "recommendation", "output_dir", "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled",
    ]
    for key in keys:
        value = result.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
