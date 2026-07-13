# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence

import pandas as pd

from football_prediction_v19.analysis.v2120_prediction_error_patterns import OUTCOMES, SAFETY_FLAGS, prepare_prediction_rows
from football_prediction_v19.analysis.v2122_rolling_team_bias_shadow_probe import normalize_probabilities
from football_prediction_v19.analysis.v2124_pl_multi_season_robustness import EDGE_BANDS, v2124_edge_band

CONFIGURATIONS = (
    "BASELINE",
    "LOW_EDGE_UNIFORM_SHRINK_005",
    "LOW_EDGE_UNIFORM_SHRINK_010",
    "LOW_EDGE_UNIFORM_SHRINK_015",
    "LOW_EDGE_DRAW_LIFT_005",
    "LOW_EDGE_DRAW_LIFT_010",
    "MEDIUM_EDGE_UNIFORM_SHRINK_005",
    "HIGH_EDGE_SHARPEN_005",
)


def prepare_probe_rows(rows: pd.DataFrame) -> pd.DataFrame:
    source = rows.copy().reset_index(drop=True)
    prepared = prepare_prediction_rows(source)
    prepared.insert(0, "season", source.get("season", pd.Series([""] * len(source))).astype(str))
    prepared["match_date"] = pd.to_datetime(prepared["match_date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("")
    valid = (
        prepared["actual_result"].isin(OUTCOMES)
        & prepared["top_probability_outcome"].isin(OUTCOMES)
        & prepared[["home_win_probability", "draw_probability", "away_win_probability"]].notna().all(axis=1)
    )
    prepared = prepared[valid].copy().reset_index(drop=True)
    prepared["edge_band"] = prepared["probability_edge"].map(v2124_edge_band)
    prepared["baseline_hit"] = prepared["top_probability_outcome"].eq(prepared["actual_result"])
    prepared["baseline_brier_loss"] = [
        brier_loss(row["home_win_probability"], row["draw_probability"], row["away_win_probability"], row["actual_result"])
        for _, row in prepared.iterrows()
    ]
    prepared["top_probability"] = prepared[["home_win_probability", "draw_probability", "away_win_probability"]].max(axis=1)
    return prepared.sort_values(["season", "match_date"], kind="stable").reset_index(drop=True)


def brier_loss(home: object, draw: object, away: object, actual_result: object) -> float:
    probabilities = normalize_probabilities(home, draw, away)
    actual = str(actual_result).upper()
    return sum((probability - float(actual == outcome)) ** 2 for probability, outcome in zip(probabilities, OUTCOMES))


def apply_shadow_configuration(rows: pd.DataFrame, configuration: str) -> pd.DataFrame:
    if configuration not in CONFIGURATIONS:
        raise ValueError(f"unknown configuration: {configuration}")
    records = []
    for _, row in rows.iterrows():
        raw_original = (
            float(row["home_win_probability"]),
            float(row["draw_probability"]),
            float(row["away_win_probability"]),
        )
        normalized_original = normalize_probabilities(*raw_original)
        shadow, adjusted = _shadow_probabilities(normalized_original, float(row["probability_edge"]), configuration)
        shadow_top = _top_outcome(*shadow) if adjusted else str(row["top_probability_outcome"])
        actual = str(row["actual_result"])
        baseline_hit = str(row["top_probability_outcome"]) == actual
        shadow_hit = shadow_top == actual
        record = row.to_dict()
        record.update({
            "configuration": configuration,
            "original_home_win_probability": raw_original[0],
            "original_draw_probability": raw_original[1],
            "original_away_win_probability": raw_original[2],
            "shadow_home_win_probability": shadow[0],
            "shadow_draw_probability": shadow[1],
            "shadow_away_win_probability": shadow[2],
            "shadow_probability_sum": sum(shadow),
            "adjustment_applied": adjusted,
            "shadow_top_outcome": shadow_top,
            "shadow_hit": shadow_hit,
            "shadow_brier_loss": brier_loss(*shadow, actual),
            "top_outcome_changed": shadow_top != str(row["top_probability_outcome"]),
            "newly_corrected": (not baseline_hit) and shadow_hit,
            "newly_broken": baseline_hit and (not shadow_hit),
        })
        records.append(record)
    return pd.DataFrame(records)


def compute_edge_band_reliability(rows: pd.DataFrame, seasons: Sequence[str]) -> pd.DataFrame:
    columns = [
        "scope", "season", "edge_band", "count", "hit_rate", "multiclass_brier_score",
        "average_top_probability", "empirical_top_hit_rate", "calibration_gap",
        "actual_home_rate", "actual_draw_rate", "actual_away_rate", "top_home_rate",
        "top_draw_rate", "top_away_rate", "mean_hit_rate", "minimum_hit_rate",
        "maximum_hit_rate", "hit_rate_range", "positive_season_count", "stable_band",
    ]
    season_baselines = {
        season: _rate(int(group["baseline_hit"].sum()), len(group))
        for season, group in rows.groupby("season")
    }
    records = []
    season_band_records: dict[str, list[dict[str, object]]] = {band: [] for band in EDGE_BANDS}
    for season in seasons:
        season_rows = rows[rows["season"].eq(season)]
        for band in EDGE_BANDS:
            group = season_rows[season_rows["edge_band"].eq(band)]
            record = _edge_metrics(group)
            record.update({"scope": "SEASON", "season": season, "edge_band": band})
            records.append(record)
            season_band_records[band].append(record)
    for band in EDGE_BANDS:
        band_records = season_band_records[band]
        rates = [float(record["hit_rate"]) for record in band_records]
        counts = [int(record["count"]) for record in band_records]
        positive_count = sum(
            int(float(record["hit_rate"]) >= float(season_baselines.get(str(record["season"]), 0.0)))
            for record in band_records if int(record["count"]) > 0
        )
        negative_count = sum(int(record["count"]) > 0 for record in band_records) - positive_count
        rate_range = round(max(rates) - min(rates), 4) if rates else 0.0
        stable = bool(
            len(band_records) == len(seasons)
            and all(count >= 30 for count in counts)
            and rate_range <= 0.08
            and max(positive_count, negative_count) >= 2
        )
        combined = rows[rows["edge_band"].eq(band)]
        aggregate = _edge_metrics(combined)
        aggregate.update({
            "scope": "CROSS_SEASON", "season": "ALL", "edge_band": band,
            "mean_hit_rate": round(sum(rates) / len(rates), 4) if rates else 0.0,
            "minimum_hit_rate": min(rates) if rates else 0.0,
            "maximum_hit_rate": max(rates) if rates else 0.0,
            "hit_rate_range": rate_range,
            "positive_season_count": int(positive_count),
            "stable_band": stable,
        })
        records.append(aggregate)
    return pd.DataFrame(records, columns=columns)


def compute_configuration_training_summary(
    training_rows: pd.DataFrame,
    *,
    fold_id: str,
    selection_seasons: Sequence[str],
    holdout_season: str,
) -> tuple[pd.DataFrame, dict[str, object]]:
    records = []
    for configuration in CONFIGURATIONS:
        applied = apply_shadow_configuration(training_rows, configuration)
        records.append({
            "fold_id": fold_id,
            "selection_seasons": ",".join(selection_seasons),
            "holdout_season": holdout_season,
            "configuration": configuration,
            "count": int(len(applied)),
            "adjustment_applied_count": int(applied["adjustment_applied"].sum()),
            "hit_rate": _rate(int(applied["shadow_hit"].sum()), len(applied)),
            "multiclass_brier_score": _mean(applied["shadow_brier_loss"]),
        })
    summary = pd.DataFrame(records)
    selected = select_best_configuration(summary)
    return summary, selected


def select_best_configuration(training_summary: pd.DataFrame) -> dict[str, object]:
    if training_summary.empty:
        return {}
    ranked = training_summary.sort_values(
        ["multiclass_brier_score", "hit_rate", "adjustment_applied_count"],
        ascending=[True, False, True], kind="stable",
    )
    return ranked.iloc[0].to_dict()


def evaluate_holdout_fold(
    holdout_rows: pd.DataFrame,
    *,
    fold_id: str,
    selection_seasons: Sequence[str],
    holdout_season: str,
    selected_configuration: str,
) -> tuple[dict[str, object], pd.DataFrame]:
    applied = apply_shadow_configuration(holdout_rows, selected_configuration)
    baseline_hit_rate = _rate(int(applied["baseline_hit"].sum()), len(applied))
    shadow_hit_rate = _rate(int(applied["shadow_hit"].sum()), len(applied))
    baseline_brier = _mean(applied["baseline_brier_loss"])
    shadow_brier = _mean(applied["shadow_brier_loss"])
    corrected = int(applied["newly_corrected"].sum())
    broken = int(applied["newly_broken"].sum())
    applied.insert(0, "fold_id", fold_id)
    applied.insert(1, "selection_seasons", ",".join(selection_seasons))
    applied.insert(2, "holdout_season", holdout_season)
    return {
        "fold_id": fold_id,
        "selection_seasons": ",".join(selection_seasons),
        "holdout_season": holdout_season,
        "selected_configuration": selected_configuration,
        "baseline_hit_rate": baseline_hit_rate,
        "shadow_hit_rate": shadow_hit_rate,
        "hit_rate_delta": round(shadow_hit_rate - baseline_hit_rate, 4),
        "baseline_brier_score": baseline_brier,
        "shadow_brier_score": shadow_brier,
        "brier_improvement": round(baseline_brier - shadow_brier, 6),
        "adjustment_applied_count": int(applied["adjustment_applied"].sum()),
        "top_outcome_change_count": int(applied["top_outcome_changed"].sum()),
        "newly_corrected_count": corrected,
        "newly_broken_count": broken,
        "net_corrected_count": int(corrected - broken),
    }, applied


def run_leave_one_season_out(
    rows: pd.DataFrame,
    seasons: Sequence[str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    training_frames = []
    fold_records = []
    holdout_frames = []
    for index, holdout_season in enumerate(seasons, start=1):
        selection_seasons = [season for season in seasons if season != holdout_season]
        training_rows = rows[rows["season"].isin(selection_seasons)].copy()
        holdout_rows = rows[rows["season"].eq(holdout_season)].copy()
        fold_id = f"FOLD_{index}"
        training_summary, selected = compute_configuration_training_summary(
            training_rows,
            fold_id=fold_id,
            selection_seasons=selection_seasons,
            holdout_season=holdout_season,
        )
        training_frames.append(training_summary)
        fold, holdout = evaluate_holdout_fold(
            holdout_rows,
            fold_id=fold_id,
            selection_seasons=selection_seasons,
            holdout_season=holdout_season,
            selected_configuration=str(selected.get("configuration", "BASELINE")),
        )
        fold_records.append(fold)
        holdout_frames.append(holdout)
    return (
        pd.concat(training_frames, ignore_index=True) if training_frames else pd.DataFrame(),
        pd.DataFrame(fold_records),
        pd.concat(holdout_frames, ignore_index=True) if holdout_frames else pd.DataFrame(),
    )


def evaluate_edge_calibration_status(folds: pd.DataFrame) -> tuple[str, str]:
    if folds.empty:
        return "EDGE_CALIBRATION_NOT_HELPFUL", "KEEP_AS_DIAGNOSTIC_ONLY"
    positive_brier = int(folds["brier_improvement"].gt(0).sum())
    mean_brier = float(folds["brier_improvement"].mean())
    mean_hit = float(folds["hit_rate_delta"].mean())
    net = int(folds["net_corrected_count"].sum())
    if positive_brier >= 2 and mean_brier > 0 and mean_hit >= -0.005 and net >= 0:
        return "EDGE_CALIBRATION_ROBUST", "EDGE_CALIBRATION_READY_FOR_EXTERNAL_VALIDATION"
    if mean_brier > 0:
        return "EDGE_CALIBRATION_UNSTABLE", "EDGE_CALIBRATION_TOO_UNSTABLE"
    return "EDGE_CALIBRATION_NOT_HELPFUL", "EDGE_CALIBRATION_NOT_HELPFUL"


def analyze_cross_season_edge_reliability(
    rows: pd.DataFrame,
    *,
    output_dir: str | Path = "outputs/v2125_cross_season_edge_reliability",
) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    prepared = prepare_probe_rows(rows)
    seasons = sorted(prepared["season"].dropna().astype(str).unique().tolist())
    edge_reliability = compute_edge_band_reliability(prepared, seasons)
    training_summary, fold_summary, holdout_rows = run_leave_one_season_out(prepared, seasons)
    status, recommendation = evaluate_edge_calibration_status(fold_summary)
    selections = Counter(fold_summary["selected_configuration"].tolist())
    most_selected, selected_count = selections.most_common(1)[0] if selections else ("", 0)
    stable_bands = edge_reliability[
        edge_reliability["scope"].eq("CROSS_SEASON") & edge_reliability["stable_band"].eq(True)  # noqa: E712
    ]
    best_stable = ""
    if not stable_bands.empty:
        best_stable = str(stable_bands.sort_values("mean_hit_rate", ascending=False, kind="stable").iloc[0]["edge_band"])
    summary = {
        "rows_loaded": int(len(rows)),
        "seasons_evaluated": int(len(seasons)),
        "holdout_fold_count": int(len(fold_summary)),
        "baseline_combined_hit_rate": _rate(int(prepared["baseline_hit"].sum()), len(prepared)),
        "baseline_combined_brier_score": _mean(prepared["baseline_brier_loss"]),
        "most_selected_configuration": most_selected,
        "same_configuration_selected_count": int(selected_count),
        "positive_brier_holdout_count": int(fold_summary["brier_improvement"].gt(0).sum()),
        "positive_hit_rate_holdout_count": int(fold_summary["hit_rate_delta"].gt(0).sum()),
        "mean_holdout_brier_improvement": _mean(fold_summary["brier_improvement"]),
        "mean_holdout_hit_rate_delta": round(float(fold_summary["hit_rate_delta"].mean()), 4) if len(fold_summary) else 0.0,
        "total_newly_corrected_count": int(fold_summary["newly_corrected_count"].sum()),
        "total_newly_broken_count": int(fold_summary["newly_broken_count"].sum()),
        "total_net_corrected_count": int(fold_summary["net_corrected_count"].sum()),
        "stable_edge_band_count": int(len(stable_bands)),
        "best_stable_edge_band": best_stable,
        "edge_calibration_status": status,
        "recommendation": recommendation,
        "output_dir": str(out).replace("\\", "/"),
        **SAFETY_FLAGS,
    }
    edge_reliability.to_csv(out / "v2125_edge_band_reliability.csv", index=False)
    training_summary.to_csv(out / "v2125_configuration_training_summary.csv", index=False)
    fold_summary.to_csv(out / "v2125_holdout_fold_summary.csv", index=False)
    holdout_rows.to_csv(out / "v2125_holdout_rows.csv", index=False)
    (out / "v2125_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "v2125_report.md").write_text(
        render_report(summary, edge_reliability, training_summary, fold_summary), encoding="utf-8",
    )
    return {
        "v2125_cross_season_edge_reliability_status": "READY",
        **summary,
        "summary_json_path": str((out / "v2125_summary.json").resolve()),
        "report_md_path": str((out / "v2125_report.md").resolve()),
    }


def render_report(summary, edge_reliability, training_summary, fold_summary):
    stable = edge_reliability[edge_reliability["scope"].eq("CROSS_SEASON")]
    return "\n".join([
        "# v2.12.5 Cross-Season Edge Reliability Holdout Probe", "",
        "Diagnostic-only leave-one-season-out selection. Holdout results never enter configuration selection.", "",
        f"- baseline_combined_hit_rate: {summary['baseline_combined_hit_rate']}",
        f"- baseline_combined_brier_score: {summary['baseline_combined_brier_score']}",
        f"- edge_calibration_status: {summary['edge_calibration_status']}",
        f"- recommendation: {summary['recommendation']}", "",
        "## Cross-season edge bands", "", _markdown_table(stable), "",
        "## Holdout folds", "", _markdown_table(fold_summary), "",
        "## Training selection metrics", "", _markdown_table(training_summary), "",
        "Safety: automatic_betting_enabled=false, staking_logic_enabled=false, roi_logic_enabled=false.",
    ])


def _shadow_probabilities(original: tuple[float, float, float], edge: float, configuration: str) -> tuple[tuple[float, float, float], bool]:
    home, draw, away = original
    if configuration.startswith("LOW_EDGE_UNIFORM_SHRINK_") and edge <= 0.05:
        alpha = {"005": 0.05, "010": 0.10, "015": 0.15}[configuration.rsplit("_", 1)[-1]]
        return normalize_probabilities(
            (1 - alpha) * home + alpha / 3,
            (1 - alpha) * draw + alpha / 3,
            (1 - alpha) * away + alpha / 3,
        ), True
    if configuration.startswith("LOW_EDGE_DRAW_LIFT_") and edge <= 0.05:
        lift = {"005": 0.005, "010": 0.010}[configuration.rsplit("_", 1)[-1]]
        available = home + away
        applied = min(lift, available)
        home_share = home / available if available else 0.5
        return normalize_probabilities(home - applied * home_share, draw + applied, away - applied * (1 - home_share)), applied > 0
    if configuration == "MEDIUM_EDGE_UNIFORM_SHRINK_005" and edge <= 0.08:
        alpha = 0.05
        return normalize_probabilities(
            (1 - alpha) * home + alpha / 3,
            (1 - alpha) * draw + alpha / 3,
            (1 - alpha) * away + alpha / 3,
        ), True
    if configuration == "HIGH_EDGE_SHARPEN_005" and edge > 0.15:
        probabilities = [home, draw, away]
        top_index = max(range(3), key=probabilities.__getitem__)
        other_indices = [index for index in range(3) if index != top_index]
        available = sum(probabilities[index] for index in other_indices)
        applied = min(0.005, available, 1.0 - probabilities[top_index])
        probabilities[top_index] += applied
        for index in other_indices:
            share = probabilities[index] / available if available else 0.5
            probabilities[index] -= applied * share
        return normalize_probabilities(*probabilities), applied > 0
    return original, False


def _edge_metrics(group: pd.DataFrame) -> dict[str, object]:
    count = len(group)
    hit_rate = _rate(int(group["baseline_hit"].sum()), count)
    average_top = _mean(group["top_probability"])
    return {
        "count": int(count),
        "hit_rate": hit_rate,
        "multiclass_brier_score": _mean(group["baseline_brier_loss"]),
        "average_top_probability": average_top,
        "empirical_top_hit_rate": hit_rate,
        "calibration_gap": round(average_top - hit_rate, 4),
        "actual_home_rate": _rate(int(group["actual_result"].eq("HOME").sum()), count),
        "actual_draw_rate": _rate(int(group["actual_result"].eq("DRAW").sum()), count),
        "actual_away_rate": _rate(int(group["actual_result"].eq("AWAY").sum()), count),
        "top_home_rate": _rate(int(group["top_probability_outcome"].eq("HOME").sum()), count),
        "top_draw_rate": _rate(int(group["top_probability_outcome"].eq("DRAW").sum()), count),
        "top_away_rate": _rate(int(group["top_probability_outcome"].eq("AWAY").sum()), count),
    }


def _top_outcome(home: float, draw: float, away: float) -> str:
    values = {"HOME": home, "DRAW": draw, "AWAY": away}
    return max(values, key=values.get)  # type: ignore[arg-type]


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
