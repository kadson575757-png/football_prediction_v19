# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Mapping

import pandas as pd

from football_prediction_v19.analysis.v2120_prediction_error_patterns import (
    OUTCOMES,
    SAFETY_FLAGS,
    prepare_prediction_rows,
)

STRATEGIES = (
    "BASELINE", "HOME_BIAS_001", "HOME_BIAS_002", "AWAY_BIAS_001",
    "AWAY_BIAS_002", "COMBINED_BIAS_001", "COMBINED_BIAS_002", "PROPORTIONAL_BIAS",
)
MINIMUM_HISTORY = 5
BIAS_THRESHOLD = 0.15
PROBABILITY_COLUMNS = ("home_win_probability", "draw_probability", "away_win_probability")


def compute_rolling_team_bias_features(rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = rows.copy() if "evaluable" in rows.columns else prepare_prediction_rows(rows)
    frame["_source_order"] = range(len(frame))
    frame["_match_date_parsed"] = pd.to_datetime(frame["match_date"], errors="coerce").dt.normalize()
    frame = frame.sort_values(["_match_date_parsed", "_source_order"], na_position="last", kind="stable").reset_index(drop=True)
    home_history: dict[str, list[dict[str, object]]] = defaultdict(list)
    away_history: dict[str, list[dict[str, object]]] = defaultdict(list)
    feature_records: dict[int, dict[str, object]] = {}
    audit_records = []

    valid = frame[frame["_match_date_parsed"].notna()]
    for target_date, day_rows in valid.groupby("_match_date_parsed", sort=True):
        for index, row in day_rows.iterrows():
            home_prior = home_history[str(row["home_team"])]
            away_prior = away_history[str(row["away_team"])]
            home_count = len(home_prior)
            away_count = len(away_prior)
            home_model_rate = _rate(sum(int(item["model_top"]) for item in home_prior), home_count)
            home_actual_rate = _rate(sum(int(item["actual_win"]) for item in home_prior), home_count)
            away_model_rate = _rate(sum(int(item["model_top"]) for item in away_prior), away_count)
            away_actual_rate = _rate(sum(int(item["actual_win"]) for item in away_prior), away_count)
            home_max = max((item["date"] for item in home_prior), default=None)
            away_max = max((item["date"] for item in away_prior), default=None)
            all_source_dates = [value for value in (home_max, away_max) if value is not None]
            max_source = max(all_source_dates, default=None)
            post_count = sum(int(item["date"] >= target_date) for item in home_prior + away_prior)
            feature_records[index] = {
                "prior_home_matches_count": int(home_count),
                "prior_model_home_top_rate": home_model_rate,
                "prior_actual_home_win_rate": home_actual_rate,
                "rolling_home_overprediction_delta": round(home_model_rate - home_actual_rate, 4),
                "home_bias_history_quality": "READY" if home_count >= MINIMUM_HISTORY else "INSUFFICIENT_HISTORY",
                "prior_away_matches_count": int(away_count),
                "prior_model_away_top_rate": away_model_rate,
                "prior_actual_away_win_rate": away_actual_rate,
                "rolling_away_overprediction_delta": round(away_model_rate - away_actual_rate, 4),
                "away_bias_history_quality": "READY" if away_count >= MINIMUM_HISTORY else "INSUFFICIENT_HISTORY",
                "home_max_source_date": _date_text(home_max),
                "away_max_source_date": _date_text(away_max),
                "max_source_date": _date_text(max_source),
                "post_match_rows_used_count": int(post_count),
            }
            audit_records.append(_audit_record(row, target_date, feature_records[index]))
        # Only after every target on this date is evaluated may this date enter history.
        for _, row in day_rows.iterrows():
            if bool(row["evaluable"]):
                home_history[str(row["home_team"])].append({
                    "date": target_date,
                    "model_top": row["top_probability_outcome"] == "HOME",
                    "actual_win": row["actual_result"] == "HOME",
                })
                away_history[str(row["away_team"])].append({
                    "date": target_date,
                    "model_top": row["top_probability_outcome"] == "AWAY",
                    "actual_win": row["actual_result"] == "AWAY",
                })

    invalid = frame[frame["_match_date_parsed"].isna()]
    for index, row in invalid.iterrows():
        feature_records[index] = _empty_rolling_features()
        audit_records.append(_audit_record(row, None, feature_records[index]))

    feature_frame = pd.DataFrame.from_dict(feature_records, orient="index")
    for column in feature_frame.columns:
        frame[column] = feature_frame[column]
    frame["shadow_evaluable"] = (
        frame["evaluable"] & frame[list(PROBABILITY_COLUMNS)].notna().all(axis=1)
    )
    frame = frame.drop(columns=["_source_order", "_match_date_parsed"])
    audit = pd.DataFrame(audit_records, columns=[
        "match_date", "home_team", "away_team", "prior_home_matches_count",
        "prior_away_matches_count", "home_max_source_date", "away_max_source_date",
        "max_source_date", "post_match_rows_used_count", "asof_audit_status",
    ])
    return frame.reset_index(drop=True), audit


def normalize_probabilities(home: object, draw: object, away: object) -> tuple[float, float, float]:
    values = [max(0.0, min(1.0, _number(value))) for value in (home, draw, away)]
    total = sum(values)
    if total <= 0:
        return (1 / 3, 1 / 3, 1 / 3)
    normalized = [round(value / total, 12) for value in values]
    first_two_sum = normalized[0] + normalized[1]
    normalized[-1] = 1.0 - first_two_sum
    for _ in range(3):
        current_sum = sum(normalized)
        if current_sum == 1.0:
            break
        normalized[-1] = math.nextafter(normalized[-1], math.inf if current_sum < 1.0 else -math.inf)
    return tuple(normalized)  # type: ignore[return-value]


def proportional_correction_strength(delta: object) -> float:
    value = _number(delta)
    if value < BIAS_THRESHOLD:
        return 0.0
    return min(0.03, max(0.0, value * 0.10))


def apply_shadow_strategy(rows: pd.DataFrame, strategy_name: str) -> pd.DataFrame:
    if strategy_name not in STRATEGIES:
        raise ValueError(f"unknown strategy: {strategy_name}")
    records = []
    for _, row in rows.iterrows():
        original = tuple(_number(row[column]) for column in PROBABILITY_COLUMNS)
        home, draw, away = normalize_probabilities(*original)
        home_shift, away_shift = _strategy_shifts(row, strategy_name)
        applied_home = min(home, home_shift)
        applied_away = min(away, away_shift)
        shadow_home, shadow_draw, shadow_away = normalize_probabilities(
            home - applied_home, draw + applied_home + applied_away, away - applied_away,
        )
        adjusted = applied_home > 0 or applied_away > 0
        if adjusted:
            shadow_top = _top_outcome(shadow_home, shadow_draw, shadow_away)
        else:
            shadow_top = str(row["top_probability_outcome"])
        actual = str(row["actual_result"])
        baseline_hit = str(row["top_probability_outcome"]) == actual
        shadow_hit = shadow_top == actual
        record = row.to_dict()
        record.update({
            "strategy_name": strategy_name,
            "original_home_win_probability": original[0],
            "original_draw_probability": original[1],
            "original_away_win_probability": original[2],
            "home_correction_applied": round(applied_home, 6),
            "away_correction_applied": round(applied_away, 6),
            "adjustment_applied": adjusted,
            "shadow_home_win_probability": shadow_home,
            "shadow_draw_probability": shadow_draw,
            "shadow_away_win_probability": shadow_away,
            "shadow_probability_sum": shadow_home + shadow_draw + shadow_away,
            "shadow_top_outcome": shadow_top,
            "baseline_hit": baseline_hit,
            "shadow_hit": shadow_hit,
            "newly_corrected": (not baseline_hit) and shadow_hit,
            "newly_broken": baseline_hit and (not shadow_hit),
            "shadow_brier_score": _row_brier(shadow_home, shadow_draw, shadow_away, actual),
        })
        records.append(record)
    return pd.DataFrame(records)


def compute_strategy_summary(strategy_rows: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "strategy_name", "evaluable_count", "adjustment_applied_count", "shadow_hit_rate",
        "delta_vs_baseline", "multiclass_brier_score", "brier_delta_vs_baseline",
        "newly_corrected_count", "newly_broken_count", "net_corrected_count",
        "draw_prediction_count", "draw_precision", "draw_recall", "home_top_hit_rate",
        "away_top_hit_rate",
    ]
    if strategy_rows.empty:
        return pd.DataFrame(columns=columns)
    baseline = strategy_rows[strategy_rows["strategy_name"].eq("BASELINE")]
    baseline_hit_rate = _rate(int(baseline["shadow_hit"].sum()), len(baseline))
    baseline_brier = round(float(baseline["shadow_brier_score"].mean()), 6) if not baseline.empty else 0.0
    records = []
    for strategy in STRATEGIES:
        group = strategy_rows[strategy_rows["strategy_name"].eq(strategy)]
        count = len(group)
        hit_rate = _rate(int(group["shadow_hit"].sum()), count)
        brier = round(float(group["shadow_brier_score"].mean()), 6) if count else 0.0
        corrected = int(group["newly_corrected"].sum()) if count else 0
        broken = int(group["newly_broken"].sum()) if count else 0
        draws = group[group["shadow_top_outcome"].eq("DRAW")]
        actual_draws = int(group["actual_result"].eq("DRAW").sum()) if count else 0
        home_top = group[group["shadow_top_outcome"].eq("HOME")]
        away_top = group[group["shadow_top_outcome"].eq("AWAY")]
        records.append({
            "strategy_name": strategy,
            "evaluable_count": int(count),
            "adjustment_applied_count": int(group["adjustment_applied"].sum()) if count else 0,
            "shadow_hit_rate": hit_rate,
            "delta_vs_baseline": round(hit_rate - baseline_hit_rate, 4),
            "multiclass_brier_score": brier,
            "brier_delta_vs_baseline": round(baseline_brier - brier, 6),
            "newly_corrected_count": corrected,
            "newly_broken_count": broken,
            "net_corrected_count": int(corrected - broken),
            "draw_prediction_count": int(len(draws)),
            "draw_precision": _rate(int(draws["actual_result"].eq("DRAW").sum()), len(draws)),
            "draw_recall": _rate(int(draws["actual_result"].eq("DRAW").sum()), actual_draws),
            "home_top_hit_rate": _rate(int(home_top["shadow_hit"].sum()), len(home_top)),
            "away_top_hit_rate": _rate(int(away_top["shadow_hit"].sum()), len(away_top)),
        })
    return pd.DataFrame(records, columns=columns)


def multiclass_brier_score(rows: pd.DataFrame) -> float:
    if rows.empty:
        return 0.0
    scores = [
        _row_brier(row["shadow_home_win_probability"], row["shadow_draw_probability"], row["shadow_away_win_probability"], row["actual_result"])
        for _, row in rows.iterrows()
    ]
    return round(sum(scores) / len(scores), 6)


def choose_best_strategy(summary: pd.DataFrame) -> dict[str, object]:
    if summary.empty:
        return {}
    ranked = summary.sort_values(
        ["shadow_hit_rate", "multiclass_brier_score", "net_corrected_count", "adjustment_applied_count"],
        ascending=[False, True, False, True], kind="stable",
    )
    return ranked.iloc[0].to_dict()


def analyze_rolling_team_bias_shadow_probe(
    rows: pd.DataFrame,
    *,
    output_dir: str | Path = "outputs/v2122_rolling_team_bias_shadow_probe",
) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    prepared = prepare_prediction_rows(rows)
    rolling, audit = compute_rolling_team_bias_features(prepared)
    evaluable = rolling[rolling["shadow_evaluable"]].copy().reset_index(drop=True)
    strategy_rows = pd.concat(
        [apply_shadow_strategy(evaluable, strategy) for strategy in STRATEGIES], ignore_index=True,
    ) if not evaluable.empty else pd.DataFrame()
    strategy_summary = compute_strategy_summary(strategy_rows)
    summary = _build_summary(prepared, evaluable, strategy_summary, audit, out)
    strategy_rows.to_csv(out / "v2122_rolling_team_bias_shadow_rows.csv", index=False)
    strategy_summary.to_csv(out / "v2122_strategy_summary.csv", index=False)
    audit.to_csv(out / "v2122_asof_audit.csv", index=False)
    (out / "v2122_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "v2122_report.md").write_text(render_report(summary, strategy_summary, audit), encoding="utf-8")
    return {
        "v2122_rolling_team_bias_shadow_probe_status": "READY",
        **summary,
        "summary_json_path": str((out / "v2122_summary.json").resolve()),
        "report_md_path": str((out / "v2122_report.md").resolve()),
    }


def render_report(summary: Mapping[str, object], strategy_summary: pd.DataFrame, audit: pd.DataFrame) -> str:
    return "\n".join([
        "# v2.12.2 Rolling Team Bias Shadow Correction Probe", "",
        "Diagnostic-only, strictly pre-match rolling team-bias corrections. Original probabilities remain unchanged.", "",
        f"- rows_loaded: {summary['rows_loaded']}",
        f"- evaluable_count: {summary['evaluable_count']}",
        f"- baseline_hit_rate: {summary['baseline_hit_rate']}",
        f"- baseline_brier_score: {summary['baseline_brier_score']}",
        f"- best_strategy_name: {summary['best_strategy_name']}",
        f"- recommendation: {summary['recommendation']}",
        f"- post_match_rows_used_count: {summary['post_match_rows_used_count']}", "",
        "## Strategy metrics", "", _markdown_table(strategy_summary), "",
        "## As-of audit status", "",
        _markdown_table(audit.groupby("asof_audit_status", dropna=False).size().reset_index(name="count")), "",
        "Safety: automatic_betting_enabled=false, staking_logic_enabled=false, roi_logic_enabled=false.",
    ])


def _build_summary(prepared, evaluable, strategy_summary, audit, output_dir):
    baseline = _strategy_record(strategy_summary, "BASELINE")
    best = choose_best_strategy(strategy_summary)
    delta = float(best.get("delta_vs_baseline", 0.0))
    brier_delta = float(best.get("brier_delta_vs_baseline", 0.0))
    net = int(best.get("net_corrected_count", 0))
    if delta >= 0.01 and net > 0:
        recommendation = "ROLLING_TEAM_BIAS_PROMISING"
    elif brier_delta > 0 and delta <= 0:
        recommendation = "ROLLING_TEAM_BIAS_CALIBRATION_ONLY"
    elif delta <= 0 and brier_delta <= 0:
        recommendation = "ROLLING_TEAM_BIAS_NOT_HELPFUL"
    else:
        recommendation = "KEEP_AS_DIAGNOSTIC_ONLY"
    return {
        "rows_loaded": int(len(prepared)),
        "evaluable_count": int(len(evaluable)),
        "baseline_hit_rate": float(baseline.get("shadow_hit_rate", 0.0)),
        "baseline_brier_score": float(baseline.get("multiclass_brier_score", 0.0)),
        "best_strategy_name": str(best.get("strategy_name", "")),
        "best_strategy_hit_rate": float(best.get("shadow_hit_rate", 0.0)),
        "best_strategy_delta_vs_baseline": delta,
        "best_strategy_brier_score": float(best.get("multiclass_brier_score", 0.0)),
        "best_strategy_brier_delta_vs_baseline": brier_delta,
        "best_strategy_adjustment_applied_count": int(best.get("adjustment_applied_count", 0)),
        "best_strategy_newly_corrected_count": int(best.get("newly_corrected_count", 0)),
        "best_strategy_newly_broken_count": int(best.get("newly_broken_count", 0)),
        "best_strategy_net_corrected_count": net,
        "post_match_rows_used_count": int(audit["post_match_rows_used_count"].sum()) if not audit.empty else 0,
        "recommendation": recommendation,
        "output_dir": str(output_dir).replace("\\", "/"),
        **SAFETY_FLAGS,
    }


def _strategy_shifts(row: pd.Series, strategy: str) -> tuple[float, float]:
    home_ready = row.get("home_bias_history_quality") == "READY"
    away_ready = row.get("away_bias_history_quality") == "READY"
    home_delta = _number(row.get("rolling_home_overprediction_delta", 0.0))
    away_delta = _number(row.get("rolling_away_overprediction_delta", 0.0))
    home_signal = home_ready and home_delta >= BIAS_THRESHOLD
    away_signal = away_ready and away_delta >= BIAS_THRESHOLD
    if strategy == "HOME_BIAS_001":
        return (0.01 if home_signal else 0.0, 0.0)
    if strategy == "HOME_BIAS_002":
        return (0.02 if home_signal else 0.0, 0.0)
    if strategy == "AWAY_BIAS_001":
        return (0.0, 0.01 if away_signal else 0.0)
    if strategy == "AWAY_BIAS_002":
        return (0.0, 0.02 if away_signal else 0.0)
    if strategy == "COMBINED_BIAS_001":
        return (0.01 if home_signal else 0.0, 0.01 if away_signal else 0.0)
    if strategy == "COMBINED_BIAS_002":
        return (0.02 if home_signal else 0.0, 0.02 if away_signal else 0.0)
    if strategy == "PROPORTIONAL_BIAS":
        return (
            proportional_correction_strength(home_delta) if home_ready else 0.0,
            proportional_correction_strength(away_delta) if away_ready else 0.0,
        )
    return (0.0, 0.0)


def _audit_record(row, target_date, features):
    post_count = int(features["post_match_rows_used_count"])
    return {
        "match_date": str(row.get("match_date", "")),
        "home_team": str(row.get("home_team", "")),
        "away_team": str(row.get("away_team", "")),
        "prior_home_matches_count": int(features["prior_home_matches_count"]),
        "prior_away_matches_count": int(features["prior_away_matches_count"]),
        "home_max_source_date": features["home_max_source_date"],
        "away_max_source_date": features["away_max_source_date"],
        "max_source_date": features["max_source_date"],
        "post_match_rows_used_count": post_count,
        "asof_audit_status": "CLEAN" if target_date is not None and post_count == 0 else "NO_VALID_TARGET_DATE" if target_date is None else "LEAKAGE_DETECTED",
    }


def _empty_rolling_features():
    return {
        "prior_home_matches_count": 0, "prior_model_home_top_rate": 0.0,
        "prior_actual_home_win_rate": 0.0, "rolling_home_overprediction_delta": 0.0,
        "home_bias_history_quality": "INSUFFICIENT_HISTORY", "prior_away_matches_count": 0,
        "prior_model_away_top_rate": 0.0, "prior_actual_away_win_rate": 0.0,
        "rolling_away_overprediction_delta": 0.0,
        "away_bias_history_quality": "INSUFFICIENT_HISTORY", "home_max_source_date": "",
        "away_max_source_date": "", "max_source_date": "", "post_match_rows_used_count": 0,
    }


def _strategy_record(summary: pd.DataFrame, strategy: str) -> dict[str, object]:
    if summary.empty:
        return {}
    matched = summary[summary["strategy_name"].eq(strategy)]
    return matched.iloc[0].to_dict() if not matched.empty else {}


def _row_brier(home: float, draw: float, away: float, actual: str) -> float:
    targets = {outcome: float(actual == outcome) for outcome in OUTCOMES}
    return (home - targets["HOME"]) ** 2 + (draw - targets["DRAW"]) ** 2 + (away - targets["AWAY"]) ** 2


def _top_outcome(home: float, draw: float, away: float) -> str:
    values = {"HOME": home, "DRAW": draw, "AWAY": away}
    return max(values, key=values.get)  # type: ignore[arg-type]


def _date_text(value: object) -> str:
    return pd.Timestamp(value).strftime("%Y-%m-%d") if value is not None else ""


def _number(value: object) -> float:
    try:
        number = float(value)
        return number if pd.notna(number) else 0.0
    except (TypeError, ValueError):
        return 0.0


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
