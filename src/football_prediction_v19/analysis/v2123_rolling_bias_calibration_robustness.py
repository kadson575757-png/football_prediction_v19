# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd

from football_prediction_v19.analysis.v2120_prediction_error_patterns import OUTCOMES, SAFETY_FLAGS, prepare_prediction_rows
from football_prediction_v19.analysis.v2122_rolling_team_bias_shadow_probe import (
    compute_rolling_team_bias_features,
    normalize_probabilities,
)

CORRECTION_STRENGTHS = {
    "AWAY_BIAS_0005": 0.005,
    "AWAY_BIAS_0010": 0.010,
    "AWAY_BIAS_0015": 0.015,
}
MINIMUM_HISTORIES = (5, 8, 10)
BIAS_THRESHOLD = 0.15
BOOTSTRAP_REPETITIONS = 2000
BOOTSTRAP_SEED = 2123


def configuration_name(strategy_name: str, minimum_history: int) -> str:
    return f"{strategy_name}_MIN_HISTORY_{minimum_history}"


def build_configurations() -> list[dict[str, object]]:
    return [
        {
            "configuration": configuration_name(strategy, minimum),
            "strategy_name": strategy,
            "minimum_history": minimum,
            "correction_strength": strength,
        }
        for strategy, strength in CORRECTION_STRENGTHS.items()
        for minimum in MINIMUM_HISTORIES
    ]


def brier_loss(home: object, draw: object, away: object, actual_result: object) -> float:
    home_p, draw_p, away_p = normalize_probabilities(home, draw, away)
    actual = str(actual_result).strip().upper()
    targets = {outcome: float(actual == outcome) for outcome in OUTCOMES}
    return (
        (home_p - targets["HOME"]) ** 2
        + (draw_p - targets["DRAW"]) ** 2
        + (away_p - targets["AWAY"]) ** 2
    )


def apply_robustness_configuration(rows: pd.DataFrame, configuration: Mapping[str, object]) -> pd.DataFrame:
    records = []
    minimum_history = int(configuration["minimum_history"])
    correction_strength = float(configuration["correction_strength"])
    for _, row in rows.iterrows():
        home, draw, away = normalize_probabilities(
            row["home_win_probability"], row["draw_probability"], row["away_win_probability"],
        )
        history_ready = int(row["prior_away_matches_count"]) >= minimum_history
        bias_signal = float(row["rolling_away_overprediction_delta"]) >= BIAS_THRESHOLD
        requested_shift = correction_strength if history_ready and bias_signal else 0.0
        applied_shift = min(away, requested_shift)
        shadow_home, shadow_draw, shadow_away = normalize_probabilities(
            home, draw + applied_shift, away - applied_shift,
        )
        baseline_loss = brier_loss(home, draw, away, row["actual_result"])
        shadow_loss = brier_loss(shadow_home, shadow_draw, shadow_away, row["actual_result"])
        baseline_top = str(row["top_probability_outcome"])
        shadow_top = _top_outcome(shadow_home, shadow_draw, shadow_away) if applied_shift > 0 else baseline_top
        target_date = _date_text(row.get("match_date", ""))
        max_source_date = str(row.get("away_max_source_date", ""))
        post_count = int(row.get("post_match_rows_used_count", 0))
        asof_clean = bool(
            target_date
            and post_count == 0
            and (not max_source_date or max_source_date < target_date)
        )
        record = row.to_dict()
        record.update({
            **configuration,
            "target_match_date": target_date,
            "max_source_date": max_source_date,
            "asof_clean": asof_clean,
            "baseline_brier_loss": baseline_loss,
            "shadow_brier_loss": shadow_loss,
            "brier_improvement": baseline_loss - shadow_loss,
            "adjustment_applied": applied_shift > 0,
            "correction_applied": applied_shift,
            "baseline_top_outcome": baseline_top,
            "shadow_top_outcome": shadow_top,
            "top_outcome_changed": shadow_top != baseline_top,
            "shadow_hit": shadow_top == str(row["actual_result"]),
            "shadow_home_win_probability": shadow_home,
            "shadow_draw_probability": shadow_draw,
            "shadow_away_win_probability": shadow_away,
        })
        records.append(record)
    return pd.DataFrame(records)


def assign_time_segments(rows: pd.DataFrame) -> pd.DataFrame:
    frame = rows.copy()
    frame["_date"] = pd.to_datetime(frame["match_date"], errors="coerce")
    frame = frame.sort_values(["_date", "match_date"], na_position="last", kind="stable").reset_index(drop=True)
    count = len(frame)
    frame["period"] = [f"PERIOD_{min(3, (index * 4) // count) + 1}" for index in range(count)] if count else []
    return frame.drop(columns=["_date"])


def compute_configuration_summary(configuration_rows: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "configuration", "strategy_name", "minimum_history", "correction_strength", "count",
        "adjustment_applied_count", "baseline_brier_score", "shadow_brier_score",
        "brier_improvement", "hit_rate", "top_outcome_change_count",
    ]
    records = []
    for configuration, group in configuration_rows.groupby("configuration", sort=False) if not configuration_rows.empty else []:
        records.append({
            "configuration": configuration,
            "strategy_name": str(group.iloc[0]["strategy_name"]),
            "minimum_history": int(group.iloc[0]["minimum_history"]),
            "correction_strength": float(group.iloc[0]["correction_strength"]),
            "count": int(len(group)),
            "adjustment_applied_count": int(group["adjustment_applied"].sum()),
            "baseline_brier_score": _mean(group["baseline_brier_loss"]),
            "shadow_brier_score": _mean(group["shadow_brier_loss"]),
            "brier_improvement": _mean(group["brier_improvement"]),
            "hit_rate": _rate(int(group["shadow_hit"].sum()), len(group)),
            "top_outcome_change_count": int(group["top_outcome_changed"].sum()),
        })
    return pd.DataFrame(records, columns=columns)


def compute_period_robustness_summary(configuration_rows: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "configuration", "period", "count", "adjustment_count", "baseline_brier_score",
        "shadow_brier_score", "brier_improvement",
    ]
    records = []
    if configuration_rows.empty:
        return pd.DataFrame(columns=columns)
    for (configuration, period), group in configuration_rows.groupby(["configuration", "period"], sort=False):
        records.append({
            "configuration": configuration,
            "period": period,
            "count": int(len(group)),
            "adjustment_count": int(group["adjustment_applied"].sum()),
            "baseline_brier_score": _mean(group["baseline_brier_loss"]),
            "shadow_brier_score": _mean(group["shadow_brier_loss"]),
            "brier_improvement": _mean(group["brier_improvement"]),
        })
    return pd.DataFrame(records, columns=columns)


def compute_team_contribution_summary(configuration_rows: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "configuration", "team", "adjustment_count", "baseline_brier_sum", "shadow_brier_sum",
        "total_brier_improvement", "average_brier_improvement", "improved_rows_count",
        "worsened_rows_count",
    ]
    records = []
    if configuration_rows.empty:
        return pd.DataFrame(columns=columns)
    for (configuration, team), group in configuration_rows.groupby(["configuration", "away_team"], sort=False):
        records.append({
            "configuration": configuration,
            "team": team,
            "adjustment_count": int(group["adjustment_applied"].sum()),
            "baseline_brier_sum": _sum(group["baseline_brier_loss"]),
            "shadow_brier_sum": _sum(group["shadow_brier_loss"]),
            "total_brier_improvement": _sum(group["brier_improvement"]),
            "average_brier_improvement": _mean(group["brier_improvement"]),
            "improved_rows_count": int(group["brier_improvement"].gt(0).sum()),
            "worsened_rows_count": int(group["brier_improvement"].lt(0).sum()),
        })
    return pd.DataFrame(records, columns=columns)


def paired_bootstrap(
    improvements: pd.Series | np.ndarray | list[float],
    *,
    repetitions: int = BOOTSTRAP_REPETITIONS,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, float]:
    values = np.asarray(improvements, dtype=float)
    if values.size == 0:
        return {
            "bootstrap_mean_improvement": 0.0,
            "bootstrap_ci_lower": 0.0,
            "bootstrap_ci_upper": 0.0,
            "probability_improvement_positive": 0.0,
        }
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, values.size, size=(repetitions, values.size))
    means = values[indices].mean(axis=1)
    return {
        "bootstrap_mean_improvement": round(float(means.mean()), 8),
        "bootstrap_ci_lower": round(float(np.quantile(means, 0.025)), 8),
        "bootstrap_ci_upper": round(float(np.quantile(means, 0.975)), 8),
        "probability_improvement_positive": round(float(np.mean(means > 0)), 4),
    }


def compute_bootstrap_summary(configuration_rows: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "configuration", "bootstrap_repetitions", "bootstrap_seed", "bootstrap_mean_improvement",
        "bootstrap_ci_lower", "bootstrap_ci_upper", "probability_improvement_positive",
    ]
    records = []
    for configuration, group in configuration_rows.groupby("configuration", sort=False) if not configuration_rows.empty else []:
        records.append({
            "configuration": configuration,
            "bootstrap_repetitions": BOOTSTRAP_REPETITIONS,
            "bootstrap_seed": BOOTSTRAP_SEED,
            **paired_bootstrap(group["brier_improvement"]),
        })
    return pd.DataFrame(records, columns=columns)


def choose_best_configuration(summary: pd.DataFrame) -> dict[str, object]:
    if summary.empty:
        return {}
    ranked = summary.sort_values(
        ["brier_improvement", "hit_rate", "top_outcome_change_count", "adjustment_applied_count"],
        ascending=[False, False, True, True], kind="stable",
    )
    return ranked.iloc[0].to_dict()


def analyze_rolling_bias_calibration_robustness(
    rows: pd.DataFrame,
    *,
    output_dir: str | Path = "outputs/v2123_rolling_bias_calibration_robustness",
) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    prepared = prepare_prediction_rows(rows)
    rolling, _ = compute_rolling_team_bias_features(prepared)
    evaluable = rolling[rolling["shadow_evaluable"]].copy().reset_index(drop=True)
    segmented = assign_time_segments(evaluable)
    configuration_rows = pd.concat(
        [apply_robustness_configuration(segmented, config) for config in build_configurations()],
        ignore_index=True,
    ) if not segmented.empty else pd.DataFrame()
    configuration_summary = compute_configuration_summary(configuration_rows)
    period_summary = compute_period_robustness_summary(configuration_rows)
    team_summary = compute_team_contribution_summary(configuration_rows)
    bootstrap_summary = compute_bootstrap_summary(configuration_rows)
    audit = _asof_audit(configuration_rows)
    summary = _build_summary(
        prepared, evaluable, configuration_summary, period_summary, team_summary,
        bootstrap_summary, audit, out,
    )
    configuration_summary.to_csv(out / "v2123_configuration_summary.csv", index=False)
    period_summary.to_csv(out / "v2123_period_robustness_summary.csv", index=False)
    team_summary.to_csv(out / "v2123_team_contribution_summary.csv", index=False)
    bootstrap_summary.to_csv(out / "v2123_bootstrap_summary.csv", index=False)
    audit.to_csv(out / "v2123_asof_audit.csv", index=False)
    (out / "v2123_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "v2123_report.md").write_text(
        render_report(summary, configuration_summary, period_summary, team_summary, bootstrap_summary),
        encoding="utf-8",
    )
    return {
        "v2123_rolling_bias_calibration_robustness_status": "READY",
        **summary,
        "summary_json_path": str((out / "v2123_summary.json").resolve()),
        "report_md_path": str((out / "v2123_report.md").resolve()),
    }


def render_report(summary, configuration_summary, period_summary, team_summary, bootstrap_summary):
    best = str(summary["best_configuration"])
    best_periods = period_summary[period_summary["configuration"].eq(best)]
    best_teams = team_summary[team_summary["configuration"].eq(best)].sort_values(
        "total_brier_improvement", ascending=False, kind="stable",
    ).head(10)
    best_bootstrap = bootstrap_summary[bootstrap_summary["configuration"].eq(best)]
    return "\n".join([
        "# v2.12.3 Rolling Bias Calibration Robustness", "",
        "Diagnostic-only robustness analysis using strictly pre-match rolling history.", "",
        f"- best_configuration: {best}",
        f"- best_brier_improvement: {summary['best_brier_improvement']}",
        f"- positive_period_count: {summary['positive_period_count']}",
        f"- largest_team_contribution_share: {summary['largest_team_contribution_share']}",
        f"- calibration_signal_status: {summary['calibration_signal_status']}",
        f"- recommendation: {summary['recommendation']}", "",
        "## Configuration summary", "", _markdown_table(configuration_summary), "",
        "## Best configuration by period", "", _markdown_table(best_periods), "",
        "## Best configuration team contributions", "", _markdown_table(best_teams), "",
        "## Best configuration bootstrap", "", _markdown_table(best_bootstrap), "",
        "Safety: automatic_betting_enabled=false, staking_logic_enabled=false, roi_logic_enabled=false.",
    ])


def _build_summary(prepared, evaluable, configs, periods, teams, bootstraps, audit, output_dir):
    best = choose_best_configuration(configs)
    best_name = str(best.get("configuration", ""))
    best_periods = periods[periods["configuration"].eq(best_name)] if not periods.empty else pd.DataFrame()
    positive_period_count = int(best_periods["brier_improvement"].gt(0).sum()) if not best_periods.empty else 0
    best_teams = teams[teams["configuration"].eq(best_name)] if not teams.empty else pd.DataFrame()
    largest_team = {}
    if not best_teams.empty:
        largest_team = best_teams.sort_values("total_brier_improvement", ascending=False, kind="stable").iloc[0].to_dict()
    total_improvement = float(best_teams["total_brier_improvement"].sum()) if not best_teams.empty else 0.0
    largest_value = max(0.0, float(largest_team.get("total_brier_improvement", 0.0)))
    largest_share = round(largest_value / total_improvement, 4) if total_improvement > 0 else 0.0
    bootstrap = _matching_record(bootstraps, "configuration", best_name)
    improvement = float(best.get("brier_improvement", 0.0))
    ci_lower = float(bootstrap.get("bootstrap_ci_lower", 0.0))
    if improvement <= 0:
        status = "CALIBRATION_SIGNAL_NOT_HELPFUL"
        recommendation = "CALIBRATION_SIGNAL_NOT_HELPFUL"
    elif ci_lower > 0 and positive_period_count >= 3 and largest_share <= 0.35:
        status = "CALIBRATION_SIGNAL_ROBUST"
        recommendation = "KEEP_CALIBRATION_SIGNAL_FOR_FURTHER_VALIDATION"
    else:
        status = "CALIBRATION_SIGNAL_UNSTABLE"
        recommendation = "CALIBRATION_SIGNAL_TOO_UNSTABLE"
    return {
        "rows_loaded": int(len(prepared)),
        "evaluable_count": int(len(evaluable)),
        "best_configuration": best_name,
        "best_minimum_history": int(best.get("minimum_history", 0)),
        "best_correction_strength": float(best.get("correction_strength", 0.0)),
        "baseline_brier_score": float(best.get("baseline_brier_score", 0.0)),
        "best_shadow_brier_score": float(best.get("shadow_brier_score", 0.0)),
        "best_brier_improvement": improvement,
        "best_hit_rate": float(best.get("hit_rate", 0.0)),
        "best_top_outcome_change_count": int(best.get("top_outcome_change_count", 0)),
        "positive_period_count": positive_period_count,
        "largest_team_contribution": str(largest_team.get("team", "")),
        "largest_team_contribution_share": largest_share,
        "bootstrap_mean_improvement": float(bootstrap.get("bootstrap_mean_improvement", 0.0)),
        "bootstrap_ci_lower": ci_lower,
        "bootstrap_ci_upper": float(bootstrap.get("bootstrap_ci_upper", 0.0)),
        "probability_improvement_positive": float(bootstrap.get("probability_improvement_positive", 0.0)),
        "post_match_rows_used_count": int(audit["post_match_rows_used_count"].sum()) if not audit.empty else 0,
        "calibration_signal_status": status,
        "recommendation": recommendation,
        "output_dir": str(output_dir).replace("\\", "/"),
        **SAFETY_FLAGS,
    }


def _asof_audit(rows: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "configuration", "match_date", "home_team", "away_team", "target_match_date",
        "max_source_date", "prior_away_matches_count", "minimum_history",
        "rolling_away_overprediction_delta", "baseline_brier_loss", "shadow_brier_loss",
        "brier_improvement", "adjustment_applied", "post_match_rows_used_count", "asof_clean",
    ]
    return rows.reindex(columns=columns)


def _matching_record(frame: pd.DataFrame, column: str, value: str) -> dict[str, object]:
    if frame.empty:
        return {}
    matched = frame[frame[column].eq(value)]
    return matched.iloc[0].to_dict() if not matched.empty else {}


def _top_outcome(home: float, draw: float, away: float) -> str:
    values = {"HOME": home, "DRAW": draw, "AWAY": away}
    return max(values, key=values.get)  # type: ignore[arg-type]


def _date_text(value: object) -> str:
    parsed = pd.to_datetime(value, errors="coerce")
    return parsed.strftime("%Y-%m-%d") if pd.notna(parsed) else ""


def _mean(values: pd.Series) -> float:
    return round(float(pd.to_numeric(values, errors="coerce").mean()), 8) if len(values) else 0.0


def _sum(values: pd.Series) -> float:
    return round(float(pd.to_numeric(values, errors="coerce").sum()), 8) if len(values) else 0.0


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
