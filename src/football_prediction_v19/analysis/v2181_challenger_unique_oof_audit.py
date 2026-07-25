"""Unique-OOF decomposition and prospective shadow gate for v2.18.1."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from football_prediction_v19.analysis.v2180_winner_validation import metrics, prepare_challenger_dataset


DEFAULT_INPUT_DIR = "outputs/v2180_hierarchical_winner_challenger"
DEFAULT_OUTPUT_DIR = "outputs/v2181_challenger_unique_oof_audit"
FIXTURE_KEY = ["competition", "season", "match_date", "home_team", "away_team"]
OUTCOMES = np.array(["HOME", "DRAW", "AWAY"])
PRIORITY = {
    "CHRONOLOGICAL_LAST_SEGMENT": 0,
    "LEAVE_ONE_SEASON_OUT": 1,
    "LEAVE_ONE_COMPETITION_OUT": 2,
}
MODEL_COLUMNS = {
    "MODEL_A_PRIMARY_WINNER_BASELINE": ("baseline", "LOW"),
    "MODEL_B_RATING_ONLY": ("rating", "LOW"),
    "MODEL_C_HIERARCHICAL_ONLY": ("hierarchical", "MEDIUM"),
    "MODEL_D_PRIMARY_PLUS_RATING_META": ("primary_rating_meta", "MEDIUM"),
    "MODEL_E_PRIMARY_PLUS_GOAL_META": ("primary_goal_meta", "MEDIUM"),
    "MODEL_F_PRIMARY_PLUS_RATING_PLUS_GOAL_META": ("primary_rating_goal_meta", "MEDIUM"),
    "MODEL_G_FULL_META_CHALLENGER": ("challenger", "HIGH"),
}
SAFETY = {
    "automatic_betting_enabled": False,
    "staking_logic_enabled": False,
    "roi_logic_enabled": False,
    "productive_betting_enabled": False,
}


def deduplicate_oof(predictions: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    frame = predictions.copy()
    frame["_priority"] = frame["fold_type"].map(PRIORITY).fillna(99)
    frame["_source"] = frame["fold_type"].astype(str) + ":" + frame["outer_holdout"].astype(str)
    frame = frame.sort_values(FIXTURE_KEY + ["_priority", "outer_fold"]).reset_index(drop=True)
    grouped = frame.groupby(FIXTURE_KEY, sort=False)
    audit = grouped.agg(
        prediction_count=("_source", "size"),
        available_oof_sources=("_source", lambda values: "|".join(values)),
        selected_oof_source=("_source", "first"),
        selected_fold_type=("fold_type", "first"),
    ).reset_index()
    unique = frame.drop_duplicates(FIXTURE_KEY, keep="first").drop(columns=["_priority", "_source"]).reset_index(drop=True)
    stats = {
        "raw_holdout_prediction_count": len(frame),
        "unique_fixture_count": len(unique),
        "duplicate_fixture_prediction_count": int((audit["prediction_count"] > 1).sum()),
        "maximum_predictions_per_fixture": int(audit["prediction_count"].max()),
    }
    return unique, audit, stats


def run_unique_oof_audit(
    project_root: str | Path,
    *,
    input_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> dict:
    root = Path(project_root)
    source = Path(input_dir) if input_dir else root / DEFAULT_INPUT_DIR
    out = Path(output_dir) if output_dir else root / DEFAULT_OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    predictions = pd.read_csv(source / "v2180_match_predictions.csv", keep_default_na=False)
    outer = pd.read_csv(source / "v2180_outer_holdout_summary.csv")
    oof = pd.read_csv(source / "v2180_oof_prediction_audit.csv")
    source_summary = json.loads((source / "v2180_summary.json").read_text(encoding="utf-8"))
    unique, duplicate_audit, counts = deduplicate_oof(predictions)
    enrichment_columns = [
        *FIXTURE_KEY, "expected_home_goals", "expected_away_goals",
        "base_probability_edge", "model_agreement",
        "maximum_model_probability_difference", "history_quality_numeric",
    ]
    enrichment = prepare_challenger_dataset(root)[enrichment_columns].drop_duplicates(FIXTURE_KEY)
    enrichment["match_date"] = enrichment["match_date"].astype(str)
    unique["match_date"] = unique["match_date"].astype(str)
    unique = unique.merge(enrichment, on=FIXTURE_KEY, how="left", validate="one_to_one")
    component = component_decomposition(unique)
    fold_metrics = _metric_levels(predictions, "FOLD_AGGREGATED")
    unique_metrics = _metric_levels(unique, "UNIQUE_OOF")
    baseline_row = component[component["model_name"].eq("MODEL_A_PRIMARY_WINNER_BASELINE")].iloc[0]
    full_row = component[component["model_name"].eq("MODEL_G_FULL_META_CHALLENGER")].iloc[0]
    simplified = component[component["model_name"].isin([
        "MODEL_D_PRIMARY_PLUS_RATING_META", "MODEL_E_PRIMARY_PLUS_GOAL_META",
        "MODEL_F_PRIMARY_PLUS_RATING_PLUS_GOAL_META",
    ])].sort_values(["hit_rate", "multiclass_brier_score", "multiclass_log_loss", "complexity_level"], ascending=[False, True, True, True]).iloc[0]
    transitions, corrected_rows = correction_transition_audit(unique)
    calibration = calibration_audit(unique)
    draw_audit = draw_failure_audit(unique)
    competition = contribution_summary(corrected_rows, "competition")
    team_rows = pd.concat([
        corrected_rows.assign(team=corrected_rows["home_team"]),
        corrected_rows.assign(team=corrected_rows["away_team"]),
    ], ignore_index=True)
    team = contribution_summary(team_rows, "team")
    correction = _correction_counts(unique)
    positive_holdout_rate = float((outer["hit_rate_delta"] > 0).mean())
    dominant_competition_share = float(competition["newly_corrected"].max() / max(1, correction["newly_corrected"]))
    dominant_team_share = float(team["newly_corrected"].max() / max(1, 2 * correction["newly_corrected"]))
    baseline_ece = float(calibration.query("model == 'BASELINE' and record_type == 'SUMMARY'")["expected_calibration_error"].iloc[0])
    challenger_ece = float(calibration.query("model == 'CHALLENGER' and record_type == 'SUMMARY'")["expected_calibration_error"].iloc[0])
    calibration_risk = challenger_ece > baseline_ece + 0.02
    unique_delta = float(full_row["hit_delta"])
    gain_ok = (
        unique_delta >= 0.02
        and full_row["multiclass_brier_score"] < baseline_row["multiclass_brier_score"]
        and full_row["multiclass_log_loss"] < baseline_row["multiclass_log_loss"]
        and correction["net_corrected"] > 0
    )
    operational_ok = (
        positive_holdout_rate >= 0.60
        and dominant_competition_share <= 0.50 and dominant_team_share <= 0.25
        and source_summary["probability_output_rate"] == 1.0
        and source_summary["oof_leakage_count"] == 0
        and source_summary["post_match_rows_used_count"] == 0
    )
    if not gain_ok:
        status, recommendation = "REJECTED_UNIQUE_OOF_GAIN_TOO_SMALL", "REJECT_CHALLENGER"
    elif calibration_risk:
        status, recommendation = "DIAGNOSTIC_ONLY_CALIBRATION_RISK", "DIAGNOSTIC_ONLY"
    elif not operational_ok:
        status, recommendation = "DIAGNOSTIC_ONLY_DUPLICATE_WEIGHTING_RISK", "DIAGNOSTIC_ONLY"
    else:
        status, recommendation = "SHADOW_APPROVED_UNIQUE_OOF_CONFIRMED", "APPROVE_FOR_PROSPECTIVE_SHADOW"
    summary = {
        "v2181_challenger_unique_oof_audit_status": "READY",
        **counts,
        "unique_oof_coverage_rate": len(unique) / max(1, source_summary["rows_loaded"]),
        "fold_baseline_hit_rate": source_summary["baseline_hit_rate"],
        "fold_challenger_hit_rate": source_summary["challenger_hit_rate"],
        "unique_baseline_hit_rate": baseline_row["hit_rate"],
        "unique_challenger_hit_rate": full_row["hit_rate"],
        "unique_hit_rate_delta": unique_delta,
        "unique_baseline_brier": baseline_row["multiclass_brier_score"],
        "unique_challenger_brier": full_row["multiclass_brier_score"],
        "unique_brier_improvement": baseline_row["multiclass_brier_score"] - full_row["multiclass_brier_score"],
        "unique_baseline_log_loss": baseline_row["multiclass_log_loss"],
        "unique_challenger_log_loss": full_row["multiclass_log_loss"],
        "unique_log_loss_improvement": baseline_row["multiclass_log_loss"] - full_row["multiclass_log_loss"],
        "best_simplified_component_model": simplified["model_name"],
        "selected_prospective_shadow_model": simplified["model_name"],
        "full_meta_hit_rate": full_row["hit_rate"],
        "simplified_model_hit_rate": simplified["hit_rate"],
        "unique_newly_corrected": correction["newly_corrected"],
        "unique_newly_broken": correction["newly_broken"],
        "unique_net_corrected": correction["net_corrected"],
        "unique_draw_precision": full_row["draw_precision"],
        "unique_draw_recall": full_row["draw_recall"],
        "unique_draw_f1": full_row["draw_f1"],
        "baseline_expected_calibration_error": baseline_ece,
        "challenger_expected_calibration_error": challenger_ece,
        "calibration_ece_delta": challenger_ece - baseline_ece,
        "positive_holdout_rate": positive_holdout_rate,
        "dominant_competition_share": dominant_competition_share,
        "dominant_team_share": dominant_team_share,
        "oof_leakage_count": int(source_summary["oof_leakage_count"] + (~oof["chronological_clean"].astype(bool)).sum()),
        "post_match_rows_used_count": int(source_summary["post_match_rows_used_count"]),
        "shadow_gate_status": status,
        "recommendation": recommendation,
        "draw_known_limitation": "DRAW_RECALL_LOW",
        **SAFETY,
    }
    duplicate_audit.to_csv(out / "v2181_duplicate_fixture_audit.csv", index=False)
    unique.to_csv(out / "v2181_unique_oof_predictions.csv", index=False)
    fold_metrics.to_csv(out / "v2181_fold_aggregated_metrics.csv", index=False)
    unique_metrics.to_csv(out / "v2181_unique_oof_metrics.csv", index=False)
    component.to_csv(out / "v2181_component_decomposition.csv", index=False)
    draw_audit.to_csv(out / "v2181_draw_failure_audit.csv", index=False)
    transitions.to_csv(out / "v2181_correction_transition_matrix.csv", index=False)
    calibration.to_csv(out / "v2181_calibration.csv", index=False)
    competition.to_csv(out / "v2181_competition_summary.csv", index=False)
    team.to_csv(out / "v2181_team_summary.csv", index=False)
    (out / "v2181_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (out / "v2181_report.md").write_text(_report(summary, component, draw_audit), encoding="utf-8")
    summary["output_dir"] = str(out.resolve())
    return summary


def component_decomposition(rows: pd.DataFrame) -> pd.DataFrame:
    baseline_probs = _probabilities(rows, "baseline")
    baseline_prediction = OUTCOMES[baseline_probs.argmax(axis=1)]
    actual = rows["actual_result"].to_numpy()
    records = []
    for model_name, (prefix, complexity) in MODEL_COLUMNS.items():
        probabilities = _probabilities(rows, prefix)
        result = metrics(rows["actual_result"], probabilities)
        predicted = OUTCOMES[probabilities.argmax(axis=1)]
        corrected = int(np.sum((baseline_prediction != actual) & (predicted == actual)))
        broken = int(np.sum((baseline_prediction == actual) & (predicted != actual)))
        records.append({
            "model_name": model_name, "complexity_level": complexity,
            "hit_rate": result["top_outcome_hit_rate"],
            "hit_delta": result["top_outcome_hit_rate"] - metrics(rows["actual_result"], baseline_probs)["top_outcome_hit_rate"],
            "multiclass_brier_score": result["multiclass_brier_score"],
            "multiclass_log_loss": result["multiclass_log_loss"],
            "draw_precision": result["draw_precision"], "draw_recall": result["draw_recall"], "draw_f1": result["draw_f1"],
            "corrected": corrected, "broken": broken, "net_corrected": corrected - broken,
        })
    return pd.DataFrame(records)


def draw_failure_audit(rows: pd.DataFrame) -> pd.DataFrame:
    probability = _probabilities(rows, "challenger")
    draw_rank = (-probability).argsort(axis=1).argsort(axis=1)[:, 1] + 1
    predicted = OUTCOMES[probability.argmax(axis=1)]
    detail_columns = list(dict.fromkeys(FIXTURE_KEY + [
        "actual_result", "competition", "expected_home_goals", "expected_away_goals",
        "rating_difference", "base_probability_edge", "model_agreement",
        "maximum_model_probability_difference",
    ]))
    detail = rows[detail_columns].copy()
    detail["record_type"] = "FIXTURE"
    detail["challenger_top_outcome"] = predicted
    detail["draw_probability"] = probability[:, 1]
    detail["draw_probability_rank"] = draw_rank
    detail["actual_draw_missed"] = detail["actual_result"].eq("DRAW") & (predicted != "DRAW")
    detail["false_draw_top"] = ~detail["actual_result"].eq("DRAW") & (predicted == "DRAW")
    detail["expected_total_goals"] = detail["expected_home_goals"] + detail["expected_away_goals"]
    summaries = [{
        "record_type": "SUMMARY",
        "group_type": "OVERALL",
        "group_value": "ALL",
        "actual_draw_count": int(detail["actual_result"].eq("DRAW").sum()),
        "draw_rank_2_count": int((detail["actual_result"].eq("DRAW") & detail["draw_probability_rank"].eq(2)).sum()),
        "average_draw_probability_actual_draw": detail.loc[detail.actual_result.eq("DRAW"), "draw_probability"].mean(),
        "average_draw_probability_non_draw": detail.loc[~detail.actual_result.eq("DRAW"), "draw_probability"].mean(),
    }]
    for group_type, series in (
        ("COMPETITION", detail["competition"]),
        ("EXPECTED_GOALS", pd.cut(detail["expected_total_goals"], [-np.inf, 2.2, 2.8, np.inf])),
        ("STRENGTH_GAP", pd.cut(detail["rating_difference"].abs(), [-np.inf, 50, 150, np.inf])),
        ("PRIMARY_EDGE", pd.cut(detail["base_probability_edge"], [-np.inf, .05, .10, np.inf])),
        ("MODEL_CONFLICT", pd.cut(detail["maximum_model_probability_difference"], [-np.inf, .05, .15, np.inf])),
    ):
        for value, group in detail.groupby(series, observed=True):
            actual_draw = group["actual_result"].eq("DRAW")
            predicted_draw = group["challenger_top_outcome"].eq("DRAW")
            tp = int((actual_draw & predicted_draw).sum())
            summaries.append({
                "record_type": "SUMMARY", "group_type": group_type, "group_value": str(value),
                "actual_draw_count": int(actual_draw.sum()),
                "draw_precision": tp / max(1, int(predicted_draw.sum())),
                "draw_recall": tp / max(1, int(actual_draw.sum())),
            })
    return pd.concat([detail, pd.DataFrame(summaries)], ignore_index=True, sort=False)


def correction_transition_audit(rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    baseline = OUTCOMES[_probabilities(rows, "baseline").argmax(axis=1)]
    challenger = OUTCOMES[_probabilities(rows, "challenger").argmax(axis=1)]
    actual = rows["actual_result"].to_numpy()
    detail = rows.copy()
    detail["baseline_top_outcome"] = baseline
    detail["challenger_top_outcome"] = challenger
    detail["newly_corrected"] = ((baseline != actual) & (challenger == actual)).astype(int)
    detail["newly_broken"] = ((baseline == actual) & (challenger != actual)).astype(int)
    transition = detail.groupby(["baseline_top_outcome", "challenger_top_outcome", "actual_result"]).agg(
        count=("actual_result", "size"), newly_corrected=("newly_corrected", "sum"), newly_broken=("newly_broken", "sum")
    ).reset_index()
    return transition, detail


def calibration_audit(rows: pd.DataFrame) -> pd.DataFrame:
    records = []
    for model, prefix in (("BASELINE", "baseline"), ("CHALLENGER", "challenger")):
        probabilities = _probabilities(rows, prefix)
        ece_parts, sharpness = [], []
        for index, outcome in enumerate(OUTCOMES):
            bucket = pd.cut(probabilities[:, index], np.linspace(0, 1, 11), include_lowest=True)
            frame = pd.DataFrame({"bucket": bucket, "probability": probabilities[:, index], "actual": rows["actual_result"].eq(outcome).astype(int)})
            for label, group in frame.groupby("bucket", observed=True):
                error = abs(group["probability"].mean() - group["actual"].mean())
                ece_parts.append(error * len(group) / (len(rows) * 3))
                records.append({
                    "record_type": "BUCKET", "model": model, "outcome": outcome, "bucket": str(label),
                    "count": len(group), "mean_predicted": group["probability"].mean(),
                    "actual_rate": group["actual"].mean(), "absolute_error": error,
                })
        top = probabilities.max(axis=1)
        top_correct = OUTCOMES[probabilities.argmax(axis=1)] == rows["actual_result"].to_numpy()
        records.append({
            "record_type": "SUMMARY", "model": model,
            "expected_calibration_error": sum(ece_parts),
            "sharpness": float(np.mean(np.std(probabilities, axis=1))),
            "mean_top_probability": float(top.mean()),
            "top_outcome_hit_rate": float(top_correct.mean()),
        })
    return pd.DataFrame(records)


def contribution_summary(rows: pd.DataFrame, group: str) -> pd.DataFrame:
    return rows.groupby(group).agg(
        fixtures=("actual_result", "size"),
        newly_corrected=("newly_corrected", "sum"),
        newly_broken=("newly_broken", "sum"),
        mean_primary_edge=("base_probability_edge", "mean"),
        mean_rating_difference=("rating_difference", "mean"),
        model_agreement_rate=("model_agreement", "mean"),
        mean_data_quality=("history_quality_numeric", "mean"),
    ).reset_index().assign(net_corrected=lambda value: value.newly_corrected - value.newly_broken)


def _metric_levels(rows: pd.DataFrame, level: str) -> pd.DataFrame:
    records = []
    for name, (prefix, _) in MODEL_COLUMNS.items():
        result = metrics(rows["actual_result"], _probabilities(rows, prefix))
        records.append({"metric_level": level, "model_name": name, **result})
    return pd.DataFrame(records)


def _probabilities(rows: pd.DataFrame, prefix: str) -> np.ndarray:
    return rows[[f"{prefix}_home_probability", f"{prefix}_draw_probability", f"{prefix}_away_probability"]].to_numpy(float)


def _correction_counts(rows: pd.DataFrame) -> dict:
    baseline = OUTCOMES[_probabilities(rows, "baseline").argmax(axis=1)]
    challenger = OUTCOMES[_probabilities(rows, "challenger").argmax(axis=1)]
    actual = rows["actual_result"].to_numpy()
    corrected = int(np.sum((baseline != actual) & (challenger == actual)))
    broken = int(np.sum((baseline == actual) & (challenger != actual)))
    return {"newly_corrected": corrected, "newly_broken": broken, "net_corrected": corrected - broken}


def _report(summary: dict, components: pd.DataFrame, draw: pd.DataFrame) -> str:
    draw_summary = draw[draw["record_type"].eq("SUMMARY") & draw.get("group_type", "").eq("OVERALL")].iloc[0]
    return f"""# v2.18.1 Challenger Unique-OOF Audit

## A. Unique-OOF construction

The deterministic priority is chronological holdout, then leave-one-season-out, then leave-one-competition-out. No result was used for selection.

- Raw holdout predictions: {summary['raw_holdout_prediction_count']}
- Unique fixtures: {summary['unique_fixture_count']}
- Duplicate fixtures: {summary['duplicate_fixture_prediction_count']}
- Unique coverage: {summary['unique_oof_coverage_rate']:.2%}

## B. Unique quality result

- Baseline hit rate: {summary['unique_baseline_hit_rate']:.4f}
- Challenger hit rate: {summary['unique_challenger_hit_rate']:.4f}
- Delta: {summary['unique_hit_rate_delta']:+.4f}
- Brier improvement: {summary['unique_brier_improvement']:+.6f}
- Log-loss improvement: {summary['unique_log_loss_improvement']:+.6f}
- Net corrected: {summary['unique_net_corrected']}

## C. Component decomposition

Best simplified component: **{summary['best_simplified_component_model']}** at {summary['simplified_model_hit_rate']:.4f}; full meta: {summary['full_meta_hit_rate']:.4f}.

## D. Draw audit

Draw remains a known limitation. Challenger recall is {summary['unique_draw_recall']:.4f}; actual draws ranked second {int(draw_summary.get('draw_rank_2_count', 0))} times.

## E. Calibration and robustness

- Baseline ECE: {summary['baseline_expected_calibration_error']:.6f}
- Challenger ECE: {summary['challenger_expected_calibration_error']:.6f}
- Positive holdout rate: {summary['positive_holdout_rate']:.2%}
- OOF leakage count: {summary['oof_leakage_count']}
- Post-match rows used: {summary['post_match_rows_used_count']}

## F. Shadow gate

**{summary['shadow_gate_status']}**

Recommendation: **{summary['recommendation']}**.

The primary winner remains authoritative. Probability blending is disabled. Draw recall remains explicitly documented as low.
"""
