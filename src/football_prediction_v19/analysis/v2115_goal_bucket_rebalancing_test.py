# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import pandas as pd


GOAL_BUCKETS = ["GOALS_0_1", "GOALS_2_3", "GOALS_4_PLUS"]
STRATEGIES = [
    "BASELINE",
    "REFERENCE_COUNT_FILTER",
    "STRONG_BUCKET_EDGE",
    "EXTREME_BUCKET_BOOST",
    "COMBINED_SINGLE_ONLY",
    "AWAY_SINGLE_ONLY",
    "COMBINED_SINGLE_WITH_REF_6_10",
    "BEST_OF_REBALANCED_RULES",
]


def run_goal_bucket_rebalancing(rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    prepared = prepare_rows(rows)
    strategy_rows = []
    summaries = []
    baseline_rate = 0.0
    for strategy in STRATEGIES:
        evaluated = apply_strategy(prepared, strategy)
        strategy_rows.append(evaluated)
        metrics = compute_strategy_metrics(evaluated, strategy)
        summaries.append(metrics)
        if strategy == "BASELINE":
            baseline_rate = float(metrics["hit_rate"])
    summary_frame = pd.DataFrame(summaries)
    summary_frame["hit_rate_delta_vs_baseline"] = (summary_frame["hit_rate"] - baseline_rate).round(4)
    best = choose_best_strategy(summary_frame)
    summary = {
        "v2115_goal_bucket_rebalancing_test_status": "READY",
        "rows_loaded": int(len(prepared)),
        "baseline_evaluable_count": int(summary_frame.loc[summary_frame["strategy_name"].eq("BASELINE"), "evaluable_count"].iloc[0]) if not summary_frame.empty else 0,
        "baseline_hit_rate": baseline_rate,
        "best_strategy_name": str(best.get("strategy_name", "")),
        "best_strategy_evaluable_count": int(best.get("evaluable_count", 0)),
        "best_strategy_hit_rate": float(best.get("hit_rate", 0.0)),
        "best_strategy_delta_vs_baseline": float(best.get("hit_rate_delta_vs_baseline", 0.0)),
        "best_strategy_goals_0_1_precision": float(best.get("goals_0_1_precision", 0.0)),
        "best_strategy_goals_0_1_recall": float(best.get("goals_0_1_recall", 0.0)),
        "best_strategy_goals_2_3_precision": float(best.get("goals_2_3_precision", 0.0)),
        "best_strategy_goals_2_3_recall": float(best.get("goals_2_3_recall", 0.0)),
        "best_strategy_goals_4_plus_precision": float(best.get("goals_4_plus_precision", 0.0)),
        "best_strategy_goals_4_plus_recall": float(best.get("goals_4_plus_recall", 0.0)),
        "best_strategy_goals_2_3_prediction_bias": int(best.get("prediction_bias_goals_2_3", 0)),
        "recommendation": recommendation(best, baseline_rate),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }
    return pd.concat(strategy_rows, ignore_index=True) if strategy_rows else pd.DataFrame(), summary_frame, summary


def prepare_rows(rows: pd.DataFrame) -> pd.DataFrame:
    frame = rows.copy()
    for column in [
        "actual_goal_bucket",
        "final_reference_top_goal_bucket",
        "combined_single_top_goal_bucket",
        "away_single_top_goal_bucket",
        "final_goal_reference_count",
        "combined_single_goal_reference_count",
        "final_reference_goals_0_1_rate",
        "final_reference_goals_2_3_rate",
        "final_reference_goals_4_plus_rate",
        "combined_single_goals_0_1_rate",
        "combined_single_goals_2_3_rate",
        "combined_single_goals_4_plus_rate",
    ]:
        if column not in frame.columns:
            frame[column] = ""
    return frame


def apply_strategy(rows: pd.DataFrame, strategy: str) -> pd.DataFrame:
    work = rows.copy()
    work["strategy_name"] = strategy
    chooser = _strategy_chooser(strategy)
    choices = [chooser(row) for _, row in work.iterrows()]
    work["strategy_predicted_goal_bucket"] = choices
    work["strategy_evaluable"] = work["strategy_predicted_goal_bucket"].isin(GOAL_BUCKETS) & work["actual_goal_bucket"].astype(str).isin(GOAL_BUCKETS)
    work["strategy_hit"] = work["strategy_evaluable"] & work["strategy_predicted_goal_bucket"].astype(str).eq(work["actual_goal_bucket"].astype(str))
    return work


def compute_strategy_metrics(rows: pd.DataFrame, strategy_name: str) -> dict[str, object]:
    evaluable = rows[rows["strategy_evaluable"].astype(bool)] if not rows.empty else pd.DataFrame()
    hit_count = int(evaluable["strategy_hit"].sum()) if not evaluable.empty else 0
    metrics: dict[str, object] = {
        "strategy_name": strategy_name,
        "evaluable_count": int(len(evaluable)),
        "hit_count": hit_count,
        "miss_count": int(len(evaluable) - hit_count),
        "hit_rate": _rate(hit_count, len(evaluable)),
    }
    for bucket in GOAL_BUCKETS:
        suffix = _suffix(bucket)
        pred = evaluable["strategy_predicted_goal_bucket"].astype(str).eq(bucket) if not evaluable.empty else pd.Series(dtype=bool)
        actual = evaluable["actual_goal_bucket"].astype(str).eq(bucket) if not evaluable.empty else pd.Series(dtype=bool)
        tp = int((pred & actual).sum()) if len(evaluable) else 0
        fp = int((pred & ~actual).sum()) if len(evaluable) else 0
        fn = int((~pred & actual).sum()) if len(evaluable) else 0
        metrics[f"predicted_{suffix}_count"] = int(pred.sum()) if len(evaluable) else 0
        metrics[f"actual_{suffix}_count"] = int(actual.sum()) if len(evaluable) else 0
        metrics[f"{suffix}_precision"] = _rate(tp, tp + fp)
        metrics[f"{suffix}_recall"] = _rate(tp, tp + fn)
        metrics[f"prediction_bias_{suffix}"] = metrics[f"predicted_{suffix}_count"] - metrics[f"actual_{suffix}_count"]
    return metrics


def choose_best_strategy(summary: pd.DataFrame) -> pd.Series:
    if summary.empty:
        return pd.Series(dtype=object)
    ranked = summary.copy()
    ranked["abs_goals_2_3_bias"] = ranked["prediction_bias_goals_2_3"].abs()
    return ranked.sort_values(["hit_rate", "evaluable_count", "abs_goals_2_3_bias"], ascending=[False, False, True]).iloc[0]


def write_rebalancing_outputs(rows: pd.DataFrame, strategy_summary: pd.DataFrame, summary: dict[str, object], output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    strategy_path = out / "v2115_goal_bucket_rebalancing_strategy_summary.csv"
    rows_path = out / "v2115_goal_bucket_rebalancing_rows.csv"
    summary_path = out / "v2115_goal_bucket_rebalancing_summary.json"
    report_path = out / "v2115_goal_bucket_rebalancing_report.md"
    strategy_summary.to_csv(strategy_path, index=False)
    rows.to_csv(rows_path, index=False)
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    report_path.write_text(render_report(summary, strategy_summary), encoding="utf-8")
    return {
        "strategy_summary_csv_path": str(strategy_path.resolve()),
        "rows_csv_path": str(rows_path.resolve()),
        "summary_json_path": str(summary_path.resolve()),
        "report_md_path": str(report_path.resolve()),
    }


def render_report(summary: dict[str, object], strategy_summary: pd.DataFrame) -> str:
    table = _strategy_markdown_table(strategy_summary)
    return "\n".join([
        "# v2.11.5 Goal Bucket Rebalancing Test",
        "",
        f"- rows_loaded: {summary['rows_loaded']}",
        f"- baseline_hit_rate: {summary['baseline_hit_rate']}",
        f"- best_strategy_name: {summary['best_strategy_name']}",
        f"- best_strategy_hit_rate: {summary['best_strategy_hit_rate']}",
        f"- recommendation: {summary['recommendation']}",
        "",
        "## Strategy Summary",
        table,
        "",
        "Safety: automatic_betting_enabled=false, staking_logic_enabled=false, roi_logic_enabled=false.",
    ])


def _strategy_markdown_table(strategy_summary: pd.DataFrame) -> str:
    if strategy_summary.empty:
        return "No strategy rows."
    columns = ["strategy_name", "evaluable_count", "hit_rate", "prediction_bias_goals_2_3"]
    lines = ["| Strategy | Evaluable | Hit Rate | GOALS_2_3 Bias |", "|---|---:|---:|---:|"]
    for _, row in strategy_summary[columns].iterrows():
        lines.append(f"| {row['strategy_name']} | {row['evaluable_count']} | {row['hit_rate']} | {row['prediction_bias_goals_2_3']} |")
    return "\n".join(lines)


def recommendation(best: pd.Series, baseline_rate: float) -> str:
    if best.empty:
        return "NOT_USEFUL"
    if float(best.get("hit_rate", 0.0)) <= baseline_rate:
        return "KEEP_BASELINE_DIAGNOSTIC_ONLY"
    if str(best.get("strategy_name", "")) == "REFERENCE_COUNT_FILTER":
        return "REFERENCE_COUNT_FILTER_PROMISING"
    if str(best.get("strategy_name", "")) in {"EXTREME_BUCKET_BOOST", "BEST_OF_REBALANCED_RULES", "STRONG_BUCKET_EDGE"}:
        return "INVESTIGATE_REBALANCED_RULES"
    return "KEEP_AS_DIAGNOSTIC_ONLY"


def _strategy_chooser(strategy: str) -> Callable[[pd.Series], str]:
    return {
        "BASELINE": lambda row: str(row.get("final_reference_top_goal_bucket", "")),
        "REFERENCE_COUNT_FILTER": _reference_count_filter,
        "STRONG_BUCKET_EDGE": _strong_bucket_edge,
        "EXTREME_BUCKET_BOOST": _extreme_bucket_boost,
        "COMBINED_SINGLE_ONLY": lambda row: str(row.get("combined_single_top_goal_bucket", "")),
        "AWAY_SINGLE_ONLY": lambda row: str(row.get("away_single_top_goal_bucket", "")),
        "COMBINED_SINGLE_WITH_REF_6_10": _combined_single_ref_6_10,
        "BEST_OF_REBALANCED_RULES": _best_of_rebalanced_rules,
    }[strategy]


def _reference_count_filter(row: pd.Series) -> str:
    return str(row.get("final_reference_top_goal_bucket", "")) if _between(row.get("final_goal_reference_count"), 6, 10) else "NO_CLEAR_TOP"


def _strong_bucket_edge(row: pd.Series) -> str:
    top, edge = _top_bucket_and_edge(row, "final_reference")
    return top if edge >= 0.15 else "NO_CLEAR_TOP"


def _extreme_bucket_boost(row: pd.Series) -> str:
    boosted = _extreme_bucket(row)
    return boosted or str(row.get("final_reference_top_goal_bucket", ""))


def _combined_single_ref_6_10(row: pd.Series) -> str:
    return str(row.get("combined_single_top_goal_bucket", "")) if _between(row.get("combined_single_goal_reference_count"), 6, 10) else "NO_CLEAR_TOP"


def _best_of_rebalanced_rules(row: pd.Series) -> str:
    if _between(row.get("final_goal_reference_count"), 6, 10):
        return str(row.get("final_reference_top_goal_bucket", ""))
    boosted = _extreme_bucket(row)
    if boosted:
        return boosted
    top, edge = _top_bucket_and_edge(row, "final_reference")
    return top if edge >= 0.15 else "NO_CLEAR_TOP"


def _extreme_bucket(row: pd.Series) -> str:
    goals_23 = _num(row.get("final_reference_goals_2_3_rate"))
    goals_01 = _num(row.get("final_reference_goals_0_1_rate"))
    goals_4p = _num(row.get("final_reference_goals_4_plus_rate"))
    if goals_4p >= 0.30 and abs(goals_4p - goals_23) <= 0.15:
        return "GOALS_4_PLUS"
    if goals_01 >= 0.30 and abs(goals_01 - goals_23) <= 0.15:
        return "GOALS_0_1"
    return ""


def _top_bucket_and_edge(row: pd.Series, prefix: str) -> tuple[str, float]:
    rates = {
        "GOALS_0_1": _num(row.get(f"{prefix}_goals_0_1_rate")),
        "GOALS_2_3": _num(row.get(f"{prefix}_goals_2_3_rate")),
        "GOALS_4_PLUS": _num(row.get(f"{prefix}_goals_4_plus_rate")),
    }
    ranked = sorted(rates.items(), key=lambda item: item[1], reverse=True)
    if not ranked or ranked[0][1] <= 0:
        return "NO_REFERENCE", 0.0
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return "NO_CLEAR_TOP", 0.0
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    return ranked[0][0], round(ranked[0][1] - second, 4)


def _between(value: object, low: int, high: int) -> bool:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return False
    return low <= number <= high


def _num(value: object) -> float:
    try:
        if str(value).strip() == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _rate(count: int, total: int) -> float:
    return round(float(count / total), 4) if total else 0.0


def _suffix(bucket: str) -> str:
    return bucket.lower()
