# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]


GOAL_BUCKETS = ["GOALS_0_1", "GOALS_2_3", "GOALS_4_PLUS"]
REFERENCE_TYPES = ["exact_pair", "combined_single", "home_single", "away_single"]
OUTPUT_DIR = "outputs/v2114_goal_bucket_bias_diagnostics"


def analyze_goal_bucket_bias(rows: str | Path | pd.DataFrame, *, output_dir: str | Path = OUTPUT_DIR, min_reference_count: int = 1) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    frame = _read_rows(rows)
    prepared = prepare_rows(frame)
    evaluable = final_evaluable(prepared, min_reference_count=min_reference_count)
    confusion = compute_confusion_matrix(evaluable)
    bucket_metrics = compute_bucket_metrics(evaluable)
    bias = compute_bias_metrics(evaluable)
    source_perf = compute_reference_source_performance(evaluable)
    type_perf = compute_reference_type_performance(prepared, min_reference_count=min_reference_count)
    count_perf = compute_reference_count_performance(evaluable)
    false_23, missed_01, missed_4p = error_lists(evaluable)
    summary = build_summary(prepared, evaluable, bucket_metrics, bias, source_perf, type_perf, count_perf, out)

    confusion.to_csv(out / "v2114_goal_bucket_confusion_matrix.csv", index=False)
    source_perf.to_csv(out / "v2114_reference_source_bucket_performance.csv", index=False)
    type_perf.to_csv(out / "v2114_reference_type_bucket_performance.csv", index=False)
    count_perf.to_csv(out / "v2114_reference_count_bucket_performance.csv", index=False)
    false_23.to_csv(out / "v2114_false_goals_2_3_rows.csv", index=False)
    missed_01.to_csv(out / "v2114_missed_goals_0_1_rows.csv", index=False)
    missed_4p.to_csv(out / "v2114_missed_goals_4_plus_rows.csv", index=False)
    (out / "v2114_goal_bucket_bias_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    (out / "v2114_goal_bucket_bias_report.md").write_text(render_report(summary), encoding="utf-8")
    return {**summary, "output_dir": str(out)}


def prepare_rows(frame: pd.DataFrame) -> pd.DataFrame:
    rows = frame.copy()
    aliases = {
        "final_reference_top_goal_bucket": ["final_reference_top_goal_bucket", "final_top_goal_bucket"],
        "actual_goal_bucket": ["actual_goal_bucket"],
        "final_goal_reference_count": ["final_goal_reference_count", "final_reference_count"],
        "final_goal_reference_source": ["final_goal_reference_source", "final_reference_source"],
    }
    for canonical, options in aliases.items():
        if canonical not in rows.columns:
            hit = next((name for name in options if name in rows.columns), None)
            rows[canonical] = rows[hit] if hit else ""
    for bucket in GOAL_BUCKETS:
        rows[bucket] = bucket
    return rows


def final_evaluable(rows: pd.DataFrame, *, min_reference_count: int = 1) -> pd.DataFrame:
    if rows.empty:
        return rows.copy()
    count = pd.to_numeric(rows.get("final_goal_reference_count", pd.Series([0] * len(rows))), errors="coerce").fillna(0)
    mask = (
        count.ge(min_reference_count)
        & rows["final_reference_top_goal_bucket"].astype(str).isin(GOAL_BUCKETS)
        & rows["actual_goal_bucket"].astype(str).isin(GOAL_BUCKETS)
    )
    out = rows[mask].copy()
    out["goal_bucket_hit_bool"] = out["final_reference_top_goal_bucket"].astype(str).eq(out["actual_goal_bucket"].astype(str))
    return out


def compute_confusion_matrix(rows: pd.DataFrame) -> pd.DataFrame:
    records = []
    for predicted in GOAL_BUCKETS:
        subset = rows[rows["final_reference_top_goal_bucket"].astype(str).eq(predicted)] if not rows.empty else pd.DataFrame()
        record = {"predicted_bucket": predicted}
        for actual in GOAL_BUCKETS:
            record[f"actual_{_suffix(actual)}"] = int(subset["actual_goal_bucket"].astype(str).eq(actual).sum()) if not subset.empty else 0
        record["total"] = sum(record[f"actual_{_suffix(actual)}"] for actual in GOAL_BUCKETS)
        records.append(record)
    return pd.DataFrame(records)


def compute_bucket_metrics(rows: pd.DataFrame) -> pd.DataFrame:
    records = []
    for bucket in GOAL_BUCKETS:
        predicted = rows["final_reference_top_goal_bucket"].astype(str).eq(bucket) if not rows.empty else pd.Series(dtype=bool)
        actual = rows["actual_goal_bucket"].astype(str).eq(bucket) if not rows.empty else pd.Series(dtype=bool)
        tp = int((predicted & actual).sum()) if len(rows) else 0
        fp = int((predicted & ~actual).sum()) if len(rows) else 0
        fn = int((~predicted & actual).sum()) if len(rows) else 0
        precision = _rate(tp, tp + fp)
        recall = _rate(tp, tp + fn)
        f1 = round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0
        records.append({"bucket": bucket, "predicted_count": int(predicted.sum()) if len(rows) else 0, "actual_count": int(actual.sum()) if len(rows) else 0, "true_positive": tp, "false_positive": fp, "false_negative": fn, "precision": precision, "recall": recall, "f1_score": f1})
    return pd.DataFrame(records)


def compute_bias_metrics(rows: pd.DataFrame) -> dict[str, object]:
    total = len(rows)
    data: dict[str, object] = {}
    for bucket in GOAL_BUCKETS:
        suffix = _suffix(bucket)
        pred = int(rows["final_reference_top_goal_bucket"].astype(str).eq(bucket).sum()) if total else 0
        actual = int(rows["actual_goal_bucket"].astype(str).eq(bucket).sum()) if total else 0
        data[f"{suffix}_prediction_bias"] = pred - actual
        data[f"{suffix}_prediction_bias_rate"] = round(_rate(pred, total) - _rate(actual, total), 4)
        data[f"predicted_{suffix}_count"] = pred
        data[f"actual_{suffix}_count"] = actual
    return data


def compute_reference_source_performance(rows: pd.DataFrame) -> pd.DataFrame:
    records = []
    for source, group in rows.groupby("final_goal_reference_source", dropna=False) if not rows.empty else []:
        hit_count = int(group["goal_bucket_hit_bool"].sum())
        record = {"final_goal_reference_source": source, "count": len(group), "hit_count": hit_count, "miss_count": len(group) - hit_count, "hit_rate": _rate(hit_count, len(group))}
        record.update(_distribution_fields(group))
        biases = {bucket: record[f"predicted_{_suffix(bucket)}_count"] - record[f"actual_{_suffix(bucket)}_count"] for bucket in GOAL_BUCKETS}
        record["most_overpredicted_bucket"] = max(biases, key=biases.get) if biases else ""
        record["most_underpredicted_bucket"] = min(biases, key=biases.get) if biases else ""
        records.append(record)
    return pd.DataFrame(records)


def compute_reference_type_performance(rows: pd.DataFrame, *, min_reference_count: int = 1) -> pd.DataFrame:
    records = []
    for ref in REFERENCE_TYPES:
        count_col = f"{ref}_goal_reference_count"
        top_col = f"{ref}_top_goal_bucket"
        if count_col not in rows.columns or top_col not in rows.columns:
            records.append({"reference_type": ref, "evaluable_count": 0, "hit_count": 0, "miss_count": 0, "hit_rate": 0.0})
            continue
        count = pd.to_numeric(rows[count_col], errors="coerce").fillna(0)
        subset = rows[count.ge(min_reference_count) & rows[top_col].astype(str).isin(GOAL_BUCKETS) & rows["actual_goal_bucket"].astype(str).isin(GOAL_BUCKETS)].copy()
        subset["pred_bucket"] = subset[top_col]
        subset["hit"] = subset["pred_bucket"].astype(str).eq(subset["actual_goal_bucket"].astype(str))
        metrics = _precision_recall_for(subset, "pred_bucket")
        record = {"reference_type": ref, "evaluable_count": len(subset), "hit_count": int(subset["hit"].sum()) if not subset.empty else 0, "miss_count": int(len(subset) - subset["hit"].sum()) if not subset.empty else 0, "hit_rate": _rate(int(subset["hit"].sum()) if not subset.empty else 0, len(subset))}
        record.update(metrics)
        record["predicted_bucket_distribution"] = _bucket_json(subset, "pred_bucket")
        record["actual_bucket_distribution"] = _bucket_json(subset, "actual_goal_bucket")
        records.append(record)
    return pd.DataFrame(records)


def compute_reference_count_performance(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return pd.DataFrame(columns=["reference_count_bucket", "count", "hit_count", "hit_rate"])
    work = rows.copy()
    work["reference_count_bucket"] = work["final_goal_reference_count"].map(reference_count_bucket)
    records = []
    for bucket in ["REF_1", "REF_2", "REF_3_5", "REF_6_10", "REF_11_PLUS"]:
        group = work[work["reference_count_bucket"].eq(bucket)]
        hit_count = int(group["goal_bucket_hit_bool"].sum()) if not group.empty else 0
        record = {"reference_count_bucket": bucket, "count": len(group), "hit_count": hit_count, "hit_rate": _rate(hit_count, len(group))}
        record.update(_distribution_fields(group))
        record.update(_precision_recall_for(group, "final_reference_top_goal_bucket"))
        records.append(record)
    return pd.DataFrame(records)


def reference_count_bucket(value: object) -> str:
    try:
        count = int(float(value))
    except (TypeError, ValueError):
        count = 0
    if count <= 1:
        return "REF_1"
    if count == 2:
        return "REF_2"
    if count <= 5:
        return "REF_3_5"
    if count <= 10:
        return "REF_6_10"
    return "REF_11_PLUS"


def error_lists(rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cols = [col for col in ["match_date", "home_team", "away_team", "actual_total_goals", "actual_goal_bucket", "final_reference_top_goal_bucket", "final_goal_reference_source", "final_goal_reference_count", "final_reference_goals_0_1_rate", "final_reference_goals_2_3_rate", "final_reference_goals_4_plus_rate"] if col in rows.columns]
    false_23 = rows[rows["final_reference_top_goal_bucket"].eq("GOALS_2_3") & ~rows["actual_goal_bucket"].eq("GOALS_2_3")]
    missed_01 = rows[rows["actual_goal_bucket"].eq("GOALS_0_1") & ~rows["final_reference_top_goal_bucket"].eq("GOALS_0_1")]
    missed_4p = rows[rows["actual_goal_bucket"].eq("GOALS_4_PLUS") & ~rows["final_reference_top_goal_bucket"].eq("GOALS_4_PLUS")]
    return false_23[cols], missed_01[cols], missed_4p[cols]


def build_summary(rows: pd.DataFrame, evaluable: pd.DataFrame, bucket_metrics: pd.DataFrame, bias: dict[str, object], source_perf: pd.DataFrame, type_perf: pd.DataFrame, count_perf: pd.DataFrame, out: Path) -> dict[str, object]:
    hit_count = int(evaluable["goal_bucket_hit_bool"].sum()) if not evaluable.empty else 0
    summary: dict[str, object] = {"v2114_goal_bucket_bias_diagnostics_status": "READY", "rows_loaded": len(rows), "evaluable_count": len(evaluable), "final_goal_bucket_hit_rate": _rate(hit_count, len(evaluable)), **bias}
    for _, row in bucket_metrics.iterrows():
        suffix = _suffix(row["bucket"])
        summary[f"{suffix}_precision"] = row["precision"]
        summary[f"{suffix}_recall"] = row["recall"]
    best_source = _best(source_perf, "final_goal_reference_source")
    best_type = _best(type_perf, "reference_type")
    best_count = _best(count_perf, "reference_count_bucket")
    summary.update({"best_reference_source": best_source[0], "best_reference_source_hit_rate": best_source[1], "best_reference_type": best_type[0], "best_reference_type_hit_rate": best_type[1], "best_reference_count_bucket": best_count[0], "best_reference_count_bucket_hit_rate": best_count[1], "main_bias_problem": main_bias_problem(bias), "recommendation": recommendation(bias, best_type[0], best_type[1], best_count[1]), "output_dir": str(out), "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False})
    return summary


def main_bias_problem(bias: dict[str, object]) -> str:
    values = {bucket: int(bias.get(f"{_suffix(bucket)}_prediction_bias", 0)) for bucket in GOAL_BUCKETS}
    over = max(values, key=values.get)
    under = min(values, key=values.get)
    return f"{over}_OVERPREDICTED__{under}_UNDERPREDICTED"


def recommendation(bias: dict[str, object], best_type: str, best_type_rate: float, best_count_rate: float) -> str:
    if abs(int(bias.get("goals_2_3_prediction_bias", 0))) >= 20:
        return "INVESTIGATE_GOAL_BUCKET_REBALANCING"
    if best_type == "combined_single" and best_type_rate >= 0.45:
        return "COMBINED_SINGLE_GOAL_BUCKET_PROMISING"
    if best_count_rate >= 0.5:
        return "REFERENCE_COUNT_FILTER_PROMISING"
    return "KEEP_AS_DIAGNOSTIC_ONLY"


def render_report(summary: dict[str, object]) -> str:
    return "\n".join([
        "# v2.11.4 Goal Bucket Bias Diagnostics",
        "",
        "## Summary",
        f"- rows_loaded: {summary['rows_loaded']}",
        f"- evaluable_count: {summary['evaluable_count']}",
        f"- final_goal_bucket_hit_rate: {summary['final_goal_bucket_hit_rate']}",
        "",
        "## Predicted vs Actual Bucket Distribution",
        f"- GOALS_0_1 bias: {summary.get('goals_0_1_prediction_bias')}",
        f"- GOALS_2_3 bias: {summary.get('goals_2_3_prediction_bias')}",
        f"- GOALS_4_PLUS bias: {summary.get('goals_4_plus_prediction_bias')}",
        "",
        "## Main Bias Problem",
        str(summary["main_bias_problem"]),
        "",
        "## Recommendation",
        str(summary["recommendation"]),
        "",
        "Safety: automatic_betting_enabled=false, staking_logic_enabled=false, roi_logic_enabled=false.",
    ])


def _precision_recall_for(rows: pd.DataFrame, pred_col: str) -> dict[str, object]:
    data: dict[str, object] = {}
    for bucket in GOAL_BUCKETS:
        pred = rows[pred_col].astype(str).eq(bucket) if not rows.empty and pred_col in rows.columns else pd.Series(dtype=bool)
        actual = rows["actual_goal_bucket"].astype(str).eq(bucket) if not rows.empty else pd.Series(dtype=bool)
        tp = int((pred & actual).sum()) if len(rows) else 0
        fp = int((pred & ~actual).sum()) if len(rows) else 0
        fn = int((~pred & actual).sum()) if len(rows) else 0
        suffix = _suffix(bucket)
        data[f"precision_{suffix}"] = _rate(tp, tp + fp)
        data[f"recall_{suffix}"] = _rate(tp, tp + fn)
    return data


def _distribution_fields(group: pd.DataFrame) -> dict[str, int]:
    return {
        **{f"predicted_{_suffix(bucket)}_count": int(group["final_reference_top_goal_bucket"].astype(str).eq(bucket).sum()) if not group.empty else 0 for bucket in GOAL_BUCKETS},
        **{f"actual_{_suffix(bucket)}_count": int(group["actual_goal_bucket"].astype(str).eq(bucket).sum()) if not group.empty else 0 for bucket in GOAL_BUCKETS},
    }


def _bucket_json(rows: pd.DataFrame, column: str) -> str:
    return json.dumps({bucket: int(rows[column].astype(str).eq(bucket).sum()) if not rows.empty and column in rows.columns else 0 for bucket in GOAL_BUCKETS}, sort_keys=True)


def _best(frame: pd.DataFrame, name_col: str) -> tuple[str, float]:
    if frame.empty or "hit_rate" not in frame.columns:
        return "", 0.0
    row = frame.sort_values("hit_rate", ascending=False).iloc[0]
    return str(row.get(name_col, "")), float(row.get("hit_rate", 0.0))


def _suffix(bucket: object) -> str:
    return str(bucket).lower().replace("goals_", "goals_")


def _rate(count: int, total: int) -> float:
    return round(float(count / total), 4) if total else 0.0


def _read_rows(rows: str | Path | pd.DataFrame) -> pd.DataFrame:
    if isinstance(rows, pd.DataFrame):
        return rows.copy()
    return pd.read_csv(rows, keep_default_na=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", required=True)
    parser.add_argument("--output-dir", default=OUTPUT_DIR)
    parser.add_argument("--min-reference-count", type=int, default=1)
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)
    result = analyze_goal_bucket_bias(args.rows, output_dir=args.output_dir, min_reference_count=args.min_reference_count)
    for key in [
        "v2114_goal_bucket_bias_diagnostics_status", "rows_loaded", "evaluable_count", "final_goal_bucket_hit_rate",
        "goals_0_1_precision", "goals_0_1_recall", "goals_2_3_precision", "goals_2_3_recall",
        "goals_4_plus_precision", "goals_4_plus_recall", "goals_0_1_prediction_bias",
        "goals_2_3_prediction_bias", "goals_4_plus_prediction_bias", "best_reference_source",
        "best_reference_source_hit_rate", "best_reference_type", "best_reference_type_hit_rate",
        "best_reference_count_bucket", "best_reference_count_bucket_hit_rate", "main_bias_problem",
        "recommendation", "output_dir", "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled",
    ]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
