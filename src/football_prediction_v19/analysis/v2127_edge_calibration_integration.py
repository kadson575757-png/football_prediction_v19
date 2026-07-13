# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Sequence

import pandas as pd

from football_prediction_v19.analysis.v2100_probability_only import _top_outcome as model_top_outcome
from football_prediction_v19.analysis.v2120_prediction_error_patterns import OUTCOMES, SAFETY_FLAGS, prepare_prediction_rows
from football_prediction_v19.analysis.v2122_rolling_team_bias_shadow_probe import normalize_probabilities
from football_prediction_v19.analysis.v2125_cross_season_edge_reliability import _shadow_probabilities as v2125_shadow_probabilities

EDGE_CALIBRATION_METHOD = "HIGH_EDGE_SHARPEN_005"
EDGE_THRESHOLD = 0.15
CALIBRATION_STRENGTH = 0.005
BASE_COLUMNS = [
    "home_win_probability", "draw_probability", "away_win_probability",
    "top_probability_outcome", "probability_edge",
]


def prepare_integration_rows(rows: pd.DataFrame) -> pd.DataFrame:
    source = rows.copy().reset_index(drop=True)
    if "actual_result" not in source.columns:
        actual_source = next((name for name in ("real_result", "result_1x2", "FTR") if name in source.columns), None)
        if actual_source:
            source["actual_result"] = source[actual_source]
    prepared = prepare_prediction_rows(source)
    for column in ["competition", "season"]:
        prepared[column] = source.get(column, pd.Series([""] * len(source))).astype(str)
    valid = (
        prepared["actual_result"].isin(OUTCOMES)
        & prepared["top_probability_outcome"].isin(OUTCOMES)
        & prepared[["home_win_probability", "draw_probability", "away_win_probability"]].notna().all(axis=1)
    )
    prepared["integration_evaluable"] = valid
    return prepared


def apply_edge_calibration_integration(rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    prepared = rows.copy() if "integration_evaluable" in rows.columns else prepare_integration_rows(rows)
    integration_records = []
    audit_records = []
    for row_index, row in prepared.iterrows():
        base_snapshot = {column: row.get(column) for column in BASE_COLUMNS}
        raw = (
            float(row["home_win_probability"]),
            float(row["draw_probability"]),
            float(row["away_win_probability"]),
        )
        edge = float(row["probability_edge"])
        calibrated, applied = _integration_formula(raw, edge)
        calibrated_top = model_top_outcome(*calibrated)
        calibrated_edge = _probability_edge(calibrated)
        source_sum = sum(raw)
        source_sum_error = abs(source_sum - 1.0)
        calibrated_sum = sum(calibrated)
        calibrated_sum_error = abs(calibrated_sum - 1.0)
        introduced_sum_error = abs(calibrated_sum_error - source_sum_error)
        expected, expected_applied = v2125_shadow_probabilities(
            normalize_probabilities(*raw), edge, EDGE_CALIBRATION_METHOD,
        )
        base_mismatch = any(not _exact_equal(row.get(column), base_snapshot[column]) for column in BASE_COLUMNS)
        unchanged_mismatch = bool(
            not applied and (
                any(not _exact_equal(calibrated[index], raw[index]) for index in range(3))
                or calibrated_top != str(row["top_probability_outcome"])
            )
        )
        formula_mismatch = bool(
            applied and (
                not expected_applied
                or any(not math.isclose(calibrated[index], expected[index], rel_tol=0.0, abs_tol=1e-12) for index in range(3))
            )
        )
        invalid = _invalid_probabilities(calibrated)
        result = row.to_dict()
        result.update({
            "edge_calibration_method": EDGE_CALIBRATION_METHOD,
            "edge_calibration_applied": applied,
            "calibrated_home_win_probability": calibrated[0],
            "calibrated_draw_probability": calibrated[1],
            "calibrated_away_win_probability": calibrated[2],
            "calibrated_top_probability_outcome": calibrated_top,
            "calibrated_top_probability": max(calibrated),
            "calibrated_probability_edge": calibrated_edge,
            "source_probability_sum": source_sum,
            "source_probability_sum_error": source_sum_error,
            "calibrated_probability_sum": calibrated_sum,
            "calibrated_probability_sum_error": calibrated_sum_error,
            "introduced_probability_sum_error": introduced_sum_error,
            "probability_sum_error": calibrated_sum_error,
            "top_outcome_changed": calibrated_top != str(row["top_probability_outcome"]),
            "calibration_delta_home": calibrated[0] - raw[0],
            "calibration_delta_draw": calibrated[1] - raw[1],
            "calibration_delta_away": calibrated[2] - raw[2],
        })
        integration_records.append(result)
        audit_records.append({
            "row_index": int(row_index),
            "dataset_source": str(row.get("dataset_source", "")),
            "competition": str(row.get("competition", "")),
            "season": str(row.get("season", "")),
            "match_date": str(row.get("match_date", "")),
            "edge_calibration_applied": applied,
            "base_probability_parity_mismatch": base_mismatch,
            "unchanged_row_mismatch": unchanged_mismatch,
            "calibration_formula_mismatch": formula_mismatch,
            "invalid_probability": invalid,
            "source_probability_sum": source_sum,
            "source_probability_sum_error": source_sum_error,
            "calibrated_probability_sum": calibrated_sum,
            "calibrated_probability_sum_error": calibrated_sum_error,
            "introduced_probability_sum_error": introduced_sum_error,
            "probability_sum_error": calibrated_sum_error,
            "top_outcome_changed": calibrated_top != str(row["top_probability_outcome"]),
        })
    return pd.DataFrame(integration_records), pd.DataFrame(audit_records)


def compute_dataset_metrics(rows: pd.DataFrame, dataset_source: str) -> dict[str, object]:
    group = rows[rows["dataset_source"].eq(dataset_source)]
    evaluable = group[group["integration_evaluable"]]
    count = len(evaluable)
    baseline_hit = evaluable["top_probability_outcome"].eq(evaluable["actual_result"])
    calibrated_hit = evaluable["calibrated_top_probability_outcome"].eq(evaluable["actual_result"])
    baseline_hit_rate = _rate(int(baseline_hit.sum()), count)
    calibrated_hit_rate = _rate(int(calibrated_hit.sum()), count)
    baseline_brier = _mean(pd.Series([
        _brier(
            row["home_win_probability"], row["draw_probability"],
            row["away_win_probability"], row["actual_result"],
        ) for _, row in evaluable.iterrows()
    ]))
    calibrated_brier = _mean(pd.Series([
        _brier(
            row["calibrated_home_win_probability"], row["calibrated_draw_probability"],
            row["calibrated_away_win_probability"], row["actual_result"],
        ) for _, row in evaluable.iterrows()
    ]))
    corrected = int((~baseline_hit & calibrated_hit).sum())
    broken = int((baseline_hit & ~calibrated_hit).sum())
    changes = evaluable[["calibration_delta_home", "calibration_delta_draw", "calibration_delta_away"]].abs()
    return {
        "dataset_source": dataset_source,
        "rows_loaded": int(len(group)),
        "evaluable_count": int(count),
        "adjustment_applied_count": int(evaluable["edge_calibration_applied"].sum()),
        "baseline_hit_rate": baseline_hit_rate,
        "calibrated_hit_rate": calibrated_hit_rate,
        "hit_rate_delta": round(calibrated_hit_rate - baseline_hit_rate, 4),
        "baseline_brier_score": baseline_brier,
        "calibrated_brier_score": calibrated_brier,
        "brier_improvement": round(baseline_brier - calibrated_brier, 6),
        "top_outcome_change_count": int(evaluable["top_outcome_changed"].sum()),
        "newly_corrected_count": corrected,
        "newly_broken_count": broken,
        "net_corrected_count": int(corrected - broken),
        "average_absolute_probability_change": round(float(changes.stack().mean()), 8) if not changes.empty else 0.0,
        "maximum_absolute_probability_change": round(float(changes.max().max()), 8) if not changes.empty else 0.0,
    }


def determine_integration_status(
    combined: dict[str, object],
    premier: dict[str, object],
    external: dict[str, object],
    parity: dict[str, object],
) -> tuple[str, str]:
    parity_failed = bool(
        int(parity["base_probability_parity_mismatch_count"])
        or int(parity["unchanged_row_mismatch_count"])
        or int(parity["calibration_formula_mismatch_count"])
        or int(parity["invalid_probability_count"])
        or float(parity["maximum_unchanged_introduced_sum_error"]) > 1e-12
        or float(parity["maximum_applied_calibrated_sum_error"]) > 1e-12
        or int(parity["applied_sum_failure_count"])
        or int(parity["unchanged_sum_regression_count"])
    )
    if parity_failed:
        return "INTEGRATION_PROBE_PARITY_FAILED", "EDGE_CALIBRATION_INTEGRATION_PARITY_FAILED"
    if float(combined["brier_improvement"]) <= 0:
        return "INTEGRATION_PROBE_NOT_HELPFUL", "EDGE_CALIBRATION_INTEGRATION_NOT_HELPFUL"
    passed = bool(
        float(premier["brier_improvement"]) > 0
        and float(external["brier_improvement"]) > 0
        and float(combined["hit_rate_delta"]) >= 0
    )
    if passed:
        return "INTEGRATION_PROBE_PASSED", "EDGE_CALIBRATION_READY_FOR_OPTIONAL_INTEGRATION"
    return "INTEGRATION_PROBE_NOT_HELPFUL", "EDGE_CALIBRATION_INTEGRATION_NOT_HELPFUL"


def analyze_edge_calibration_integration(
    premier_rows: pd.DataFrame,
    external_rows: pd.DataFrame,
    *,
    output_dir: str | Path = "outputs/v2127_edge_calibration_integration_probe",
) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    premier = prepare_integration_rows(premier_rows)
    premier["dataset_source"] = "PREMIER_LEAGUE_MULTI_SEASON"
    external = prepare_integration_rows(external_rows)
    external["dataset_source"] = "EXTERNAL_LEAGUES"
    combined_input = pd.concat([premier, external], ignore_index=True)
    integration_rows, parity_audit = apply_edge_calibration_integration(combined_input)
    premier_metrics = compute_dataset_metrics(integration_rows, "PREMIER_LEAGUE_MULTI_SEASON")
    external_metrics = compute_dataset_metrics(integration_rows, "EXTERNAL_LEAGUES")
    integration_rows["dataset_source_combined"] = "COMBINED"
    combined_view = integration_rows.copy()
    combined_view["dataset_source"] = "COMBINED"
    combined_metrics = compute_dataset_metrics(combined_view, "COMBINED")
    dataset_summary = pd.DataFrame([premier_metrics, external_metrics, combined_metrics])
    parity = {
        "base_probability_parity_mismatch_count": int(parity_audit["base_probability_parity_mismatch"].sum()),
        "unchanged_row_mismatch_count": int(parity_audit["unchanged_row_mismatch"].sum()),
        "calibration_formula_mismatch_count": int(parity_audit["calibration_formula_mismatch"].sum()),
        "invalid_probability_count": int(parity_audit["invalid_probability"].sum()),
        "maximum_probability_sum_error": float(parity_audit["probability_sum_error"].max()) if len(parity_audit) else 0.0,
        "maximum_source_probability_sum_error": float(parity_audit["source_probability_sum_error"].max()) if len(parity_audit) else 0.0,
        "maximum_unchanged_introduced_sum_error": _conditional_max(
            parity_audit, ~parity_audit["edge_calibration_applied"], "introduced_probability_sum_error",
        ),
        "maximum_applied_calibrated_sum_error": _conditional_max(
            parity_audit, parity_audit["edge_calibration_applied"], "calibrated_probability_sum_error",
        ),
        "source_sum_warning_count": int((parity_audit["source_probability_sum_error"] > 1e-12).sum()),
        "applied_sum_failure_count": int((
            parity_audit["edge_calibration_applied"]
            & (parity_audit["calibrated_probability_sum_error"] > 1e-12)
        ).sum()),
        "unchanged_sum_regression_count": int((
            ~parity_audit["edge_calibration_applied"]
            & (parity_audit["introduced_probability_sum_error"] > 1e-12)
        ).sum()),
        "top_outcome_change_count": int(parity_audit["top_outcome_changed"].sum()),
    }
    status, recommendation = determine_integration_status(combined_metrics, premier_metrics, external_metrics, parity)
    summary = {
        **combined_metrics,
        "premier_league_brier_improvement": float(premier_metrics["brier_improvement"]),
        "external_league_brier_improvement": float(external_metrics["brier_improvement"]),
        **parity,
        "integration_probe_status": status,
        "recommendation": recommendation,
        "output_dir": str(out).replace("\\", "/"),
        **SAFETY_FLAGS,
    }
    summary.pop("dataset_source", None)
    integration_rows.to_csv(out / "v2127_integration_rows.csv", index=False)
    dataset_summary.to_csv(out / "v2127_dataset_summary.csv", index=False)
    parity_audit.to_csv(out / "v2127_parity_audit.csv", index=False)
    (out / "v2127_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "v2127_report.md").write_text(
        render_report(summary, dataset_summary, parity), encoding="utf-8",
    )
    return {
        "v2127_edge_calibration_integration_probe_status": "READY",
        **summary,
        "summary_json_path": str((out / "v2127_summary.json").resolve()),
        "report_md_path": str((out / "v2127_report.md").resolve()),
    }


def render_report(summary: dict[str, object], dataset_summary: pd.DataFrame, parity: dict[str, object]) -> str:
    sections = [
        "# v2.12.7 Edge Calibration Integration Probe", "",
        "## 1. Summary", "", f"- integration_probe_status: {summary['integration_probe_status']}", "",
        "## 2. Fixed Calibration Method", "", f"- method: {EDGE_CALIBRATION_METHOD}",
        f"- threshold: probability_edge > {EDGE_THRESHOLD}", f"- strength: {CALIBRATION_STRENGTH}", "",
        "## 3. Base Probability Parity", "", _markdown_table(pd.DataFrame([parity])), "",
        "## 4. Probability Validity", "", f"- invalid_probability_count: {summary['invalid_probability_count']}",
        f"- maximum_probability_sum_error: {summary['maximum_probability_sum_error']}",
        f"- maximum_source_probability_sum_error: {summary['maximum_source_probability_sum_error']}",
        f"- maximum_unchanged_introduced_sum_error: {summary['maximum_unchanged_introduced_sum_error']}",
        f"- maximum_applied_calibrated_sum_error: {summary['maximum_applied_calibrated_sum_error']}",
        f"- source_sum_warning_count: {summary['source_sum_warning_count']}",
        f"- applied_sum_failure_count: {summary['applied_sum_failure_count']}",
        f"- unchanged_sum_regression_count: {summary['unchanged_sum_regression_count']}", "",
        "## 5. Premier League Reproduction", "", _markdown_table(dataset_summary[dataset_summary['dataset_source'].eq('PREMIER_LEAGUE_MULTI_SEASON')]), "",
        "## 6. External League Reproduction", "", _markdown_table(dataset_summary[dataset_summary['dataset_source'].eq('EXTERNAL_LEAGUES')]), "",
        "## 7. Combined Evaluation", "", _markdown_table(dataset_summary[dataset_summary['dataset_source'].eq('COMBINED')]), "",
        "## 8. Integration Recommendation", "", f"- recommendation: {summary['recommendation']}", "",
        "Safety: automatic_betting_enabled=false, staking_logic_enabled=false, roi_logic_enabled=false.",
    ]
    return "\n".join(sections)


def _integration_formula(raw: tuple[float, float, float], edge: float) -> tuple[tuple[float, float, float], bool]:
    if edge <= EDGE_THRESHOLD:
        return raw, False
    normalized_base = normalize_probabilities(*raw)
    probabilities = list(normalized_base)
    top_outcome = model_top_outcome(*normalized_base)
    top_index = OUTCOMES.index(top_outcome)
    other_indices = [index for index in range(3) if index != top_index]
    available = sum(probabilities[index] for index in other_indices)
    applied = min(CALIBRATION_STRENGTH, available, 1.0 - probabilities[top_index])
    probabilities[top_index] += applied
    for index in other_indices:
        share = probabilities[index] / available if available else 0.5
        probabilities[index] -= applied * share
    return normalize_probabilities(*probabilities), applied > 0


def _probability_edge(probabilities: tuple[float, float, float]) -> float:
    ranked = sorted(zip(OUTCOMES, probabilities, strict=True), key=lambda item: item[1], reverse=True)
    return round(ranked[0][1] - ranked[1][1], 12)


def _invalid_probabilities(probabilities: tuple[float, float, float]) -> bool:
    return any(not math.isfinite(value) or value < 0 or value > 1 for value in probabilities)


def _brier(home: object, draw: object, away: object, actual_result: object) -> float:
    probabilities = normalize_probabilities(home, draw, away)
    actual = str(actual_result)
    return sum((probability - float(actual == outcome)) ** 2 for probability, outcome in zip(probabilities, OUTCOMES))


def _exact_equal(left: object, right: object) -> bool:
    if isinstance(left, float) or isinstance(right, float):
        try:
            return float(left) == float(right)
        except (TypeError, ValueError):
            return False
    return left == right


def _mean(values: pd.Series) -> float:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    return round(float(numeric.mean()), 6) if len(numeric) else 0.0


def _conditional_max(frame: pd.DataFrame, mask: pd.Series, column: str) -> float:
    values = frame.loc[mask, column]
    return float(values.max()) if len(values) else 0.0


def _rate(count: int, total: int) -> float:
    return round(float(count / total), 4) if total else 0.0


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return ""
    columns = list(frame.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(column, "")) for column in columns) + " |")
    return "\n".join(lines)
