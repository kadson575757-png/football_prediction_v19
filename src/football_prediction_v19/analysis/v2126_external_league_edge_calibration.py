# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Sequence

import pandas as pd

from football_prediction_v19.analysis.v2120_prediction_error_patterns import OUTCOMES, SAFETY_FLAGS, prepare_prediction_rows
from football_prediction_v19.analysis.v2122_rolling_team_bias_shadow_probe import normalize_probabilities
from football_prediction_v19.analysis.v2125_cross_season_edge_reliability import apply_shadow_configuration

FIXED_CONFIGURATION = "HIGH_EDGE_SHARPEN_005"
EXPECTED_FIXTURE_COUNTS = {"La Liga": 380, "Bundesliga": 306, "Serie A": 380}
EMPTY_EXTERNAL_ROW_COLUMNS = [
    "fixed_configuration", "competition", "season", "match_date", "home_team", "away_team",
    "actual_result", "top_probability_outcome", "probability_edge", "baseline_hit",
    "baseline_brier_loss", "original_home_win_probability", "original_draw_probability",
    "original_away_win_probability", "shadow_home_win_probability", "shadow_draw_probability",
    "shadow_away_win_probability", "adjustment_applied", "shadow_top_outcome", "shadow_hit",
    "shadow_brier_loss", "top_outcome_changed", "newly_corrected", "newly_broken",
    "target_match_date", "maximum_source_date", "asof_clean", "post_match_rows_used_count",
]


def apply_fixed_high_edge_sharpen(rows: pd.DataFrame) -> pd.DataFrame:
    """Apply the pre-registered v2.12.5 configuration without selection or tuning."""
    prepared = prepare_external_rows(rows)
    return apply_shadow_configuration(prepared, FIXED_CONFIGURATION)


def prepare_external_rows(rows: pd.DataFrame) -> pd.DataFrame:
    source = rows.copy().reset_index(drop=True)
    if "actual_result" not in source.columns:
        actual_source = next((name for name in ("real_result", "result_1x2", "FTR") if name in source.columns), None)
        if actual_source:
            source["actual_result"] = source[actual_source]
    if "match_date" not in source.columns:
        date_source = next((name for name in ("resolved_match_date", "input_match_date", "Date") if name in source.columns), None)
        if date_source:
            source["match_date"] = source[date_source]
    prepared = prepare_prediction_rows(source)
    prepared.insert(0, "competition", source.get("competition", pd.Series([""] * len(source))).astype(str))
    prepared.insert(1, "season", source.get("season", pd.Series([""] * len(source))).astype(str))
    valid = (
        prepared["actual_result"].isin(OUTCOMES)
        & prepared["top_probability_outcome"].isin(OUTCOMES)
        & prepared[["home_win_probability", "draw_probability", "away_win_probability"]].notna().all(axis=1)
    )
    prepared["external_evaluable"] = valid
    prepared["baseline_hit"] = valid & prepared["top_probability_outcome"].eq(prepared["actual_result"])
    prepared["baseline_brier_loss"] = [
        _brier(row) if bool(row["external_evaluable"]) else float("nan") for _, row in prepared.iterrows()
    ]
    prepared["target_match_date"] = prepared["match_date"].map(_date_text)
    maximum_source = _first_existing(source, ["maximum_source_date", "max_source_date", "as_of_date"])
    prepared["maximum_source_date"] = maximum_source.map(_date_text)
    post = _first_existing(source, ["post_match_rows_used_count"])
    prepared["post_match_rows_used_count"] = pd.to_numeric(post, errors="coerce").fillna(0).astype(int)
    guard = _first_existing(source, ["asof_guard_status", "asof_status"]).astype(str).str.upper()
    prepared["asof_clean"] = [
        bool(target and post_count == 0 and (not maximum or maximum < target) and "LEAK" not in status)
        for target, maximum, post_count, status in zip(
            prepared["target_match_date"], prepared["maximum_source_date"],
            prepared["post_match_rows_used_count"], guard,
        )
    ]
    return prepared


def compute_competition_season_metrics(
    rows: pd.DataFrame,
    *,
    competition: str,
    season: str,
    expected_fixture_count: int,
    fixtures_found: int | None = None,
    load_status: str = "LOADED",
    load_reason: str = "",
) -> tuple[dict[str, object], pd.DataFrame]:
    prepared = rows if "external_evaluable" in rows.columns else prepare_external_rows(rows)
    evaluable = prepared[prepared["external_evaluable"]].copy().reset_index(drop=True)
    applied = apply_shadow_configuration(evaluable, FIXED_CONFIGURATION) if not evaluable.empty else pd.DataFrame()
    baseline_hit_rate = _rate(int(applied["baseline_hit"].sum()), len(applied)) if not applied.empty else 0.0
    shadow_hit_rate = _rate(int(applied["shadow_hit"].sum()), len(applied)) if not applied.empty else 0.0
    baseline_brier = _mean(applied["baseline_brier_loss"]) if not applied.empty else 0.0
    shadow_brier = _mean(applied["shadow_brier_loss"]) if not applied.empty else 0.0
    found = int(len(prepared) if fixtures_found is None else fixtures_found)
    evaluable_count = len(applied)
    complete = bool(found >= expected_fixture_count and evaluable_count >= expected_fixture_count)
    status = "READY" if complete else ("PARTIAL" if found or evaluable_count else "UNAVAILABLE")
    corrected = int(applied["newly_corrected"].sum()) if not applied.empty else 0
    broken = int(applied["newly_broken"].sum()) if not applied.empty else 0
    average_change = 0.0
    if not applied.empty:
        total_change = (
            (applied["shadow_home_win_probability"] - applied["original_home_win_probability"]).abs()
            + (applied["shadow_draw_probability"] - applied["original_draw_probability"]).abs()
            + (applied["shadow_away_win_probability"] - applied["original_away_win_probability"]).abs()
        ) / 3
        average_change = _mean(total_change)
    metrics = {
        "competition": competition,
        "season": season,
        "competition_season_status": status,
        "load_status": load_status,
        "load_reason": load_reason,
        "expected_fixture_count": int(expected_fixture_count),
        "fixtures_found": found,
        "fixtures_analyzed": int(len(prepared)),
        "evaluable_count": int(evaluable_count),
        "probability_output_rate": _rate(evaluable_count, found),
        "baseline_hit_rate": baseline_hit_rate,
        "shadow_hit_rate": shadow_hit_rate,
        "hit_rate_delta": round(shadow_hit_rate - baseline_hit_rate, 4),
        "baseline_brier_score": baseline_brier,
        "shadow_brier_score": shadow_brier,
        "brier_improvement": round(baseline_brier - shadow_brier, 6),
        "adjustment_applied_count": int(applied["adjustment_applied"].sum()) if not applied.empty else 0,
        "top_outcome_change_count": int(applied["top_outcome_changed"].sum()) if not applied.empty else 0,
        "newly_corrected_count": corrected,
        "newly_broken_count": broken,
        "net_corrected_count": int(corrected - broken),
        "average_probability_change": average_change,
        "post_match_rows_used_count": int(prepared["post_match_rows_used_count"].sum()) if not prepared.empty else 0,
        "asof_violation_count": int((~prepared["asof_clean"]).sum()) if not prepared.empty else 0,
    }
    if not applied.empty:
        applied.insert(0, "fixed_configuration", FIXED_CONFIGURATION)
    return metrics, applied


def compute_competition_summary(
    external_rows: pd.DataFrame,
    competition_season_summary: pd.DataFrame,
    competitions: Sequence[str],
) -> pd.DataFrame:
    records = []
    for competition in competitions:
        rows = external_rows[external_rows["competition"].eq(competition)] if not external_rows.empty else pd.DataFrame()
        seasons = competition_season_summary[competition_season_summary["competition"].eq(competition)]
        complete = seasons[seasons["competition_season_status"].eq("READY")]
        baseline_hits = int(rows["baseline_hit"].sum()) if not rows.empty else 0
        shadow_hits = int(rows["shadow_hit"].sum()) if not rows.empty else 0
        baseline_brier = _mean(rows["baseline_brier_loss"]) if not rows.empty else 0.0
        shadow_brier = _mean(rows["shadow_brier_loss"]) if not rows.empty else 0.0
        records.append({
            "competition": competition,
            "seasons_evaluated": int(len(complete)),
            "evaluable_count": int(len(rows)),
            "baseline_hit_rate": _rate(baseline_hits, len(rows)),
            "shadow_hit_rate": _rate(shadow_hits, len(rows)),
            "mean_hit_rate_delta": round(float(seasons["hit_rate_delta"].mean()), 4) if len(seasons) else 0.0,
            "baseline_brier_score": baseline_brier,
            "shadow_brier_score": shadow_brier,
            "total_brier_improvement": round(baseline_brier - shadow_brier, 6),
            "positive_brier_season_count": int(seasons["brier_improvement"].gt(0).sum()) if len(seasons) else 0,
            "negative_brier_season_count": int(seasons["brier_improvement"].lt(0).sum()) if len(seasons) else 0,
            "top_outcome_change_count": int(rows["top_outcome_changed"].sum()) if not rows.empty else 0,
        })
    return pd.DataFrame(records)


def evaluate_external_validation_status(
    competition_season_summary: pd.DataFrame,
    competition_summary: pd.DataFrame,
    external_rows: pd.DataFrame,
    *,
    competitions_requested: int,
) -> tuple[str, str]:
    complete = competition_season_summary[competition_season_summary["competition_season_status"].eq("READY")]
    competitions_evaluated = int(complete["competition"].nunique()) if not complete.empty else 0
    if competitions_evaluated < 2 or len(complete) < 6:
        return "EXTERNAL_DATA_INSUFFICIENT", "EXTERNAL_DATA_INSUFFICIENT"
    baseline_brier = _mean(external_rows["baseline_brier_loss"]) if not external_rows.empty else 0.0
    shadow_brier = _mean(external_rows["shadow_brier_loss"]) if not external_rows.empty else 0.0
    combined_improvement = baseline_brier - shadow_brier
    positive_ratio = float(complete["brier_improvement"].gt(0).mean()) if len(complete) else 0.0
    worst_competition = float(competition_summary["total_brier_improvement"].min()) if len(competition_summary) else 0.0
    hit_delta = _rate(int(external_rows["shadow_hit"].sum()), len(external_rows)) - _rate(int(external_rows["baseline_hit"].sum()), len(external_rows)) if len(external_rows) else 0.0
    post_count = int(external_rows["post_match_rows_used_count"].sum()) if len(external_rows) else 0
    if combined_improvement <= 0:
        return "EXTERNAL_EDGE_CALIBRATION_NOT_HELPFUL", "EDGE_CALIBRATION_EXTERNAL_VALIDATION_FAILED"
    if positive_ratio >= 0.65 and worst_competition >= -0.0005 and hit_delta >= -0.002 and post_count == 0:
        return "EXTERNAL_EDGE_CALIBRATION_ROBUST", "EDGE_CALIBRATION_READY_FOR_INTEGRATION_PROBE"
    return "EXTERNAL_EDGE_CALIBRATION_MIXED", "EDGE_CALIBRATION_REQUIRES_MORE_VALIDATION"


def evaluate_external_league_edge_calibration(
    competition_season_inputs: Mapping[tuple[str, str], pd.DataFrame],
    *,
    competitions: Sequence[str],
    seasons: Sequence[str],
    load_info: Mapping[tuple[str, str], Mapping[str, object]] | None = None,
    expected_fixture_counts: Mapping[str, int] = EXPECTED_FIXTURE_COUNTS,
    output_dir: str | Path = "outputs/v2126_external_league_edge_calibration",
) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    info = load_info or {}
    metric_records = []
    row_frames = []
    audit_frames = []
    for competition in competitions:
        expected = int(expected_fixture_counts.get(competition, 0))
        for season in seasons:
            key = (competition, season)
            raw = competition_season_inputs.get(key, pd.DataFrame())
            prepared = prepare_external_rows(raw)
            metadata = info.get(key, {})
            metrics, applied = compute_competition_season_metrics(
                prepared,
                competition=competition,
                season=season,
                expected_fixture_count=expected,
                fixtures_found=int(metadata.get("fixtures_found", len(raw))),
                load_status=str(metadata.get("load_status", "LOADED" if len(raw) else "MISSING")),
                load_reason=str(metadata.get("load_reason", "" if len(raw) else "no rows available")),
            )
            metric_records.append(metrics)
            if not applied.empty:
                row_frames.append(applied)
            audit = prepared.reindex(columns=[
                "competition", "season", "match_date", "home_team", "away_team",
                "target_match_date", "maximum_source_date", "asof_clean", "post_match_rows_used_count",
            ])
            audit_frames.append(audit)
    competition_season_summary = pd.DataFrame(metric_records)
    external_rows = pd.concat(row_frames, ignore_index=True) if row_frames else pd.DataFrame(columns=EMPTY_EXTERNAL_ROW_COLUMNS)
    audit = pd.concat(audit_frames, ignore_index=True) if audit_frames else pd.DataFrame()
    competition_summary = compute_competition_summary(external_rows, competition_season_summary, competitions)
    status, recommendation = evaluate_external_validation_status(
        competition_season_summary, competition_summary, external_rows,
        competitions_requested=len(competitions),
    )
    complete = competition_season_summary[competition_season_summary["competition_season_status"].eq("READY")]
    baseline_hit = _rate(int(external_rows["baseline_hit"].sum()), len(external_rows)) if len(external_rows) else 0.0
    shadow_hit = _rate(int(external_rows["shadow_hit"].sum()), len(external_rows)) if len(external_rows) else 0.0
    baseline_brier = _mean(external_rows["baseline_brier_loss"]) if len(external_rows) else 0.0
    shadow_brier = _mean(external_rows["shadow_brier_loss"]) if len(external_rows) else 0.0
    corrected = int(external_rows["newly_corrected"].sum()) if len(external_rows) else 0
    broken = int(external_rows["newly_broken"].sum()) if len(external_rows) else 0
    summary = {
        "competitions_requested": int(len(competitions)),
        "competitions_evaluated": int(complete["competition"].nunique()) if not complete.empty else 0,
        "competition_seasons_evaluated": int(len(complete)),
        "combined_evaluable_count": int(len(external_rows)),
        "combined_baseline_hit_rate": baseline_hit,
        "combined_shadow_hit_rate": shadow_hit,
        "combined_hit_rate_delta": round(shadow_hit - baseline_hit, 4),
        "combined_baseline_brier_score": baseline_brier,
        "combined_shadow_brier_score": shadow_brier,
        "combined_brier_improvement": round(baseline_brier - shadow_brier, 6),
        "positive_brier_competition_season_count": int(complete["brier_improvement"].gt(0).sum()) if len(complete) else 0,
        "negative_brier_competition_season_count": int(complete["brier_improvement"].lt(0).sum()) if len(complete) else 0,
        "positive_brier_competition_count": int(competition_summary["total_brier_improvement"].gt(0).sum()) if len(competition_summary) else 0,
        "total_adjustment_applied_count": int(external_rows["adjustment_applied"].sum()) if len(external_rows) else 0,
        "total_top_outcome_change_count": int(external_rows["top_outcome_changed"].sum()) if len(external_rows) else 0,
        "total_newly_corrected_count": corrected,
        "total_newly_broken_count": broken,
        "total_net_corrected_count": int(corrected - broken),
        "post_match_rows_used_count": int(audit["post_match_rows_used_count"].sum()) if len(audit) else 0,
        "external_validation_status": status,
        "recommendation": recommendation,
        "output_dir": str(out).replace("\\", "/"),
        **SAFETY_FLAGS,
    }
    competition_season_summary.to_csv(out / "v2126_competition_season_summary.csv", index=False)
    competition_summary.to_csv(out / "v2126_competition_summary.csv", index=False)
    external_rows.to_csv(out / "v2126_external_rows.csv", index=False)
    audit.to_csv(out / "v2126_asof_audit.csv", index=False)
    (out / "v2126_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "v2126_report.md").write_text(
        render_report(summary, competition_season_summary, competition_summary), encoding="utf-8",
    )
    return {
        "v2126_external_league_edge_calibration_status": "READY",
        **summary,
        "summary_json_path": str((out / "v2126_summary.json").resolve()),
        "report_md_path": str((out / "v2126_report.md").resolve()),
    }


def render_report(summary, competition_season_summary, competition_summary):
    return "\n".join([
        "# v2.12.6 External League Edge Calibration Validation", "",
        f"Pre-registered configuration: {FIXED_CONFIGURATION}. No external-data strategy selection.", "",
        f"- competition_seasons_evaluated: {summary['competition_seasons_evaluated']}",
        f"- combined_brier_improvement: {summary['combined_brier_improvement']}",
        f"- external_validation_status: {summary['external_validation_status']}",
        f"- recommendation: {summary['recommendation']}", "",
        "## Competition-season results", "", _markdown_table(competition_season_summary), "",
        "## Competition results", "", _markdown_table(competition_summary), "",
        "Safety: automatic_betting_enabled=false, staking_logic_enabled=false, roi_logic_enabled=false.",
    ])


def _brier(row: pd.Series) -> float:
    probabilities = normalize_probabilities(
        row["home_win_probability"], row["draw_probability"], row["away_win_probability"],
    )
    actual = str(row["actual_result"])
    return sum((probability - float(actual == outcome)) ** 2 for probability, outcome in zip(probabilities, OUTCOMES))


def _first_existing(frame: pd.DataFrame, candidates: Sequence[str]) -> pd.Series:
    selected = next((column for column in candidates if column in frame.columns), None)
    return frame[selected] if selected else pd.Series([""] * len(frame), index=frame.index, dtype=object)


def _date_text(value: object) -> str:
    parsed = pd.to_datetime(value, errors="coerce")
    return parsed.strftime("%Y-%m-%d") if pd.notna(parsed) else ""


def _mean(values: pd.Series) -> float:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    return round(float(numeric.mean()), 6) if len(numeric) else 0.0


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
