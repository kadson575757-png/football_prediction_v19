# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from football_prediction_v19.analysis.v2120_prediction_error_patterns import (
    ERROR_TYPES,
    OUTCOMES,
    SAFETY_FLAGS,
    prepare_prediction_rows,
)
from football_prediction_v19.analysis.v2122_rolling_team_bias_shadow_probe import normalize_probabilities

EXPECTED_PL_FIXTURE_COUNT = 380
EDGE_BANDS = (
    "EDGE_0_03", "EDGE_3_05", "EDGE_5_08", "EDGE_8_10", "EDGE_10_15", "EDGE_GT_15",
)


def v2124_edge_band(value: object) -> str:
    try:
        edge = float(value)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if pd.isna(edge) or edge < 0:
        return "UNKNOWN"
    if edge <= 0.03:
        return "EDGE_0_03"
    if edge <= 0.05:
        return "EDGE_3_05"
    if edge <= 0.08:
        return "EDGE_5_08"
    if edge <= 0.10:
        return "EDGE_8_10"
    if edge <= 0.15:
        return "EDGE_10_15"
    return "EDGE_GT_15"


def prepare_season_rows(rows: pd.DataFrame, season: str) -> pd.DataFrame:
    source_rows = rows.copy()
    if "actual_result" not in source_rows.columns:
        actual_source = next((name for name in ("real_result", "result_1x2", "FTR") if name in source_rows.columns), None)
        if actual_source:
            source_rows["actual_result"] = source_rows[actual_source]
    if "match_date" not in source_rows.columns:
        date_source = next((name for name in ("resolved_match_date", "input_match_date", "Date") if name in source_rows.columns), None)
        if date_source:
            source_rows["match_date"] = source_rows[date_source]
    prepared = prepare_prediction_rows(source_rows)
    prepared.insert(0, "season", season)
    prepared["probability_output"] = (
        prepared["top_probability_outcome"].isin(OUTCOMES)
        & prepared[["home_win_probability", "draw_probability", "away_win_probability"]].notna().all(axis=1)
    )
    prepared["result_known"] = prepared["actual_result"].isin(OUTCOMES)
    prepared["evaluable"] = prepared["probability_output"] & prepared["result_known"]
    prepared["prediction_hit"] = prepared["evaluable"] & prepared["top_probability_outcome"].eq(prepared["actual_result"])
    prepared["edge_band"] = prepared["probability_edge"].map(v2124_edge_band)
    prepared["top_probability"] = prepared[["home_win_probability", "draw_probability", "away_win_probability"]].max(axis=1)
    prepared["wrong_high_confidence"] = (
        prepared["evaluable"] & ~prepared["prediction_hit"]
        & (prepared["top_probability"].ge(0.45) | prepared["probability_edge"].ge(0.10))
    )
    source = source_rows.reset_index(drop=True)
    prepared["target_match_date"] = prepared["match_date"].map(_date_text)
    prepared["maximum_source_date"] = _first_existing(source, ["maximum_source_date", "max_source_date", "as_of_date"])
    prepared["maximum_source_date"] = prepared["maximum_source_date"].map(_date_text)
    raw_post = _first_existing(source, ["post_match_rows_used_count"])
    prepared["post_match_rows_used_count"] = pd.to_numeric(raw_post, errors="coerce").fillna(0).astype(int)
    guard = _first_existing(source, ["asof_guard_status", "asof_status"]).astype(str).str.upper()
    prepared["asof_clean"] = [
        bool(target and post == 0 and (not maximum or maximum < target) and "LEAK" not in status)
        for target, maximum, post, status in zip(
            prepared["target_match_date"], prepared["maximum_source_date"],
            prepared["post_match_rows_used_count"], guard,
        )
    ]
    prepared["brier_loss"] = [
        _brier_loss(row) if bool(row["evaluable"]) else np.nan for _, row in prepared.iterrows()
    ]
    return prepared


def compute_season_metrics(
    rows: pd.DataFrame,
    season: str,
    *,
    expected_fixture_count: int = EXPECTED_PL_FIXTURE_COUNT,
    load_status: str = "LOADED",
    load_reason: str = "",
) -> dict[str, object]:
    prepared = rows if "brier_loss" in rows.columns else prepare_season_rows(rows, season)
    evaluable = prepared[prepared["evaluable"]]
    probability_rows = prepared[prepared["probability_output"]]
    count = len(evaluable)
    hits = int(evaluable["prediction_hit"].sum())
    hit_rate = _rate(hits, count)
    average_top = _mean(evaluable["top_probability"])
    status = "READY" if count >= expected_fixture_count else ("PARTIAL" if len(prepared) else "UNAVAILABLE")
    metrics: dict[str, object] = {
        "season": season,
        "season_status": status,
        "load_status": load_status,
        "load_reason": load_reason,
        "expected_fixture_count": int(expected_fixture_count),
        "fixtures_found": int(len(prepared)),
        "fixtures_analyzed": int(len(prepared)),
        "result_known_count": int(prepared["result_known"].sum()),
        "probability_output_count": int(len(probability_rows)),
        "probability_output_rate": _rate(len(probability_rows), len(prepared)),
        "evaluable_count": int(count),
        "top_probability_hit_count": hits,
        "top_probability_miss_count": int(count - hits),
        "top_probability_hit_rate": hit_rate,
        "multiclass_brier_score": _mean(evaluable["brier_loss"]),
        "average_top_probability": average_top,
        "calibration_gap": round(average_top - hit_rate, 4),
        "wrong_high_confidence_count": int(evaluable["wrong_high_confidence"].sum()),
        "post_match_rows_used_count": int(prepared["post_match_rows_used_count"].sum()),
        "asof_clean_count": int(prepared["asof_clean"].sum()),
        "asof_violation_count": int((~prepared["asof_clean"]).sum()),
    }
    for outcome in OUTCOMES:
        predicted = evaluable[evaluable["top_probability_outcome"].eq(outcome)]
        metrics[f"{outcome.lower()}_top_count"] = int(len(predicted))
        metrics[f"{outcome.lower()}_top_hit_rate"] = _rate(int(predicted["prediction_hit"].sum()), len(predicted))
        metrics[f"actual_{outcome.lower()}_count"] = int(evaluable["actual_result"].eq(outcome).sum())
    metrics["actual_draw_rate"] = _rate(int(evaluable["actual_result"].eq("DRAW").sum()), count)
    metrics["predicted_draw_top_rate"] = _rate(int(evaluable["top_probability_outcome"].eq("DRAW").sum()), count)
    errors = evaluable[~evaluable["prediction_hit"]]["error_type"]
    metrics["biggest_error_type"] = _most_common(errors.tolist())
    metrics["biggest_error_type_count"] = int(errors.eq(metrics["biggest_error_type"]).sum()) if len(errors) else 0
    return metrics


def compute_error_type_by_season(combined_rows: pd.DataFrame, seasons: Sequence[str]) -> pd.DataFrame:
    records = []
    for season in seasons:
        group = combined_rows[combined_rows["season"].eq(season) & combined_rows["evaluable"]]
        for error_type in ERROR_TYPES:
            if error_type == "UNKNOWN":
                continue
            count = int(group["error_type"].eq(error_type).sum())
            records.append({
                "season": season,
                "error_type": error_type,
                "count": count,
                "rate": _rate(count, len(group)),
            })
    return pd.DataFrame(records, columns=["season", "error_type", "count", "rate"])


def compute_edge_band_by_season(combined_rows: pd.DataFrame, seasons: Sequence[str]) -> pd.DataFrame:
    columns = [
        "season", "edge_band", "count", "hit_rate", "actual_draw_rate",
        "home_top_rate", "draw_top_rate", "away_top_rate",
    ]
    records = []
    for season in seasons:
        season_rows = combined_rows[combined_rows["season"].eq(season) & combined_rows["evaluable"]]
        for band in EDGE_BANDS:
            group = season_rows[season_rows["edge_band"].eq(band)]
            count = len(group)
            records.append({
                "season": season,
                "edge_band": band,
                "count": int(count),
                "hit_rate": _rate(int(group["prediction_hit"].sum()), count),
                "actual_draw_rate": _rate(int(group["actual_result"].eq("DRAW").sum()), count),
                "home_top_rate": _rate(int(group["top_probability_outcome"].eq("HOME").sum()), count),
                "draw_top_rate": _rate(int(group["top_probability_outcome"].eq("DRAW").sum()), count),
                "away_top_rate": _rate(int(group["top_probability_outcome"].eq("AWAY").sum()), count),
            })
    return pd.DataFrame(records, columns=columns)


def compute_cross_season_summary(
    season_summary: pd.DataFrame,
    combined_rows: pd.DataFrame,
    error_summary: pd.DataFrame,
    edge_summary: pd.DataFrame,
    *,
    seasons_requested: int,
) -> dict[str, object]:
    complete = season_summary[season_summary["season_status"].eq("READY")]
    evaluable = combined_rows[combined_rows["evaluable"]]
    hit_rates = complete["top_probability_hit_rate"].astype(float) if not complete.empty else pd.Series(dtype=float)
    hit_span = float(hit_rates.max() - hit_rates.min()) if len(hit_rates) else 0.0
    error_counts = error_summary[~error_summary["error_type"].eq("HIT")].groupby("error_type")["count"].sum() if not error_summary.empty else pd.Series(dtype=int)
    common_error = str(error_counts.idxmax()) if len(error_counts) and int(error_counts.max()) > 0 else ""
    biggest_errors = complete["biggest_error_type"].astype(str).tolist()
    biggest_consensus = Counter(biggest_errors).most_common(1)[0][1] if biggest_errors else 0
    draw_never = int(complete["predicted_draw_top_rate"].le(0.01).sum()) if not complete.empty else 0
    home_draw_biggest = int(complete["biggest_error_type"].eq("HOME_TOP_ACTUAL_DRAW").sum()) if not complete.empty else 0
    stable_error = bool(len(complete) >= 2 and biggest_consensus >= 2 and draw_never >= 2 and hit_span <= 0.05)
    worst_edges = []
    for season in complete["season"].astype(str):
        season_edges = edge_summary[edge_summary["season"].eq(season) & edge_summary["count"].gt(0)]
        if not season_edges.empty:
            worst_edges.append(str(season_edges.sort_values("hit_rate", kind="stable").iloc[0]["edge_band"]))
    edge_consensus = Counter(worst_edges).most_common(1)[0][1] if worst_edges else 0
    stable_edge = bool(len(complete) >= 2 and edge_consensus >= 2)
    if len(complete) < 2:
        recommendation = "MULTI_SEASON_DATA_INSUFFICIENT"
    elif stable_error:
        recommendation = "MODEL_ERROR_PATTERN_STABLE"
    else:
        recommendation = "MODEL_ERROR_PATTERN_SEASON_SPECIFIC"
    return {
        "seasons_requested": int(seasons_requested),
        "seasons_evaluated": int(len(complete)),
        "combined_evaluable_count": int(len(evaluable)),
        "combined_hit_rate": _rate(int(evaluable["prediction_hit"].sum()), len(evaluable)),
        "combined_brier_score": _mean(evaluable["brier_loss"]),
        "mean_season_hit_rate": round(float(hit_rates.mean()), 4) if len(hit_rates) else 0.0,
        "minimum_season_hit_rate": round(float(hit_rates.min()), 4) if len(hit_rates) else 0.0,
        "maximum_season_hit_rate": round(float(hit_rates.max()), 4) if len(hit_rates) else 0.0,
        "season_hit_rate_standard_deviation": round(float(hit_rates.std(ddof=0)), 4) if len(hit_rates) else 0.0,
        "most_common_error_type_across_seasons": common_error,
        "seasons_with_draw_never_top": draw_never,
        "seasons_with_home_top_actual_draw_as_biggest_error": home_draw_biggest,
        "stable_error_pattern": stable_error,
        "stable_edge_pattern": stable_edge,
        "post_match_rows_used_count": int(combined_rows["post_match_rows_used_count"].sum()) if not combined_rows.empty else 0,
        "recommendation": recommendation,
        **SAFETY_FLAGS,
    }


def evaluate_pl_multi_season_robustness(
    season_inputs: Mapping[str, pd.DataFrame],
    *,
    seasons: Sequence[str],
    season_load_info: Mapping[str, Mapping[str, object]] | None = None,
    expected_fixture_count: int = EXPECTED_PL_FIXTURE_COUNT,
    output_dir: str | Path = "outputs/v2124_pl_multi_season_robustness",
) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    combined_frames = []
    season_records = []
    load_info = season_load_info or {}
    for season in seasons:
        raw = season_inputs.get(season, pd.DataFrame())
        prepared = prepare_season_rows(raw, season)
        combined_frames.append(prepared)
        info = load_info.get(season, {})
        season_records.append(compute_season_metrics(
            prepared,
            season,
            expected_fixture_count=expected_fixture_count,
            load_status=str(info.get("load_status", "LOADED" if len(raw) else "MISSING")),
            load_reason=str(info.get("load_reason", "" if len(raw) else "no season rows available")),
        ))
    combined = pd.concat(combined_frames, ignore_index=True) if combined_frames else prepare_season_rows(pd.DataFrame(), "")
    season_summary = pd.DataFrame(season_records)
    error_summary = compute_error_type_by_season(combined, seasons)
    edge_summary = compute_edge_band_by_season(combined, seasons)
    audit = combined.reindex(columns=[
        "season", "match_date", "home_team", "away_team", "target_match_date",
        "maximum_source_date", "asof_clean", "post_match_rows_used_count",
    ])
    summary = compute_cross_season_summary(
        season_summary, combined, error_summary, edge_summary, seasons_requested=len(seasons),
    )
    summary["output_dir"] = str(out).replace("\\", "/")
    season_summary.to_csv(out / "v2124_season_summary.csv", index=False)
    combined.to_csv(out / "v2124_combined_rows.csv", index=False)
    error_summary.to_csv(out / "v2124_error_type_by_season.csv", index=False)
    edge_summary.to_csv(out / "v2124_edge_band_by_season.csv", index=False)
    audit.to_csv(out / "v2124_asof_audit.csv", index=False)
    (out / "v2124_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "v2124_report.md").write_text(
        render_report(summary, season_summary, error_summary, edge_summary), encoding="utf-8",
    )
    return {
        "v2124_pl_multi_season_robustness_status": "READY",
        **summary,
        "summary_json_path": str((out / "v2124_summary.json").resolve()),
        "report_md_path": str((out / "v2124_report.md").resolve()),
    }


def render_report(summary, season_summary, error_summary, edge_summary):
    return "\n".join([
        "# v2.12.4 Premier League Multi-Season Robustness Evaluation", "",
        "Unchanged probability model evaluated with pre-match-only inputs.", "",
        f"- seasons_evaluated: {summary['seasons_evaluated']}",
        f"- combined_hit_rate: {summary['combined_hit_rate']}",
        f"- combined_brier_score: {summary['combined_brier_score']}",
        f"- recommendation: {summary['recommendation']}",
        f"- post_match_rows_used_count: {summary['post_match_rows_used_count']}", "",
        "## Season status and metrics", "", _markdown_table(season_summary), "",
        "## Error types by season", "", _markdown_table(error_summary), "",
        "## Edge bands by season", "", _markdown_table(edge_summary), "",
        "Safety: automatic_betting_enabled=false, staking_logic_enabled=false, roi_logic_enabled=false.",
    ])


def _brier_loss(row: pd.Series) -> float:
    home, draw, away = normalize_probabilities(
        row["home_win_probability"], row["draw_probability"], row["away_win_probability"],
    )
    actual = str(row["actual_result"])
    return sum((probability - float(actual == outcome)) ** 2 for probability, outcome in zip((home, draw, away), OUTCOMES))


def _first_existing(frame: pd.DataFrame, candidates: Sequence[str]) -> pd.Series:
    selected = next((column for column in candidates if column in frame.columns), None)
    return frame[selected] if selected else pd.Series([""] * len(frame), index=frame.index, dtype=object)


def _most_common(values: Sequence[str]) -> str:
    counts = Counter(values)
    return counts.most_common(1)[0][0] if counts else ""


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
