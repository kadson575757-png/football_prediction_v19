# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v24_metrics import enrich_prediction_frame, load_results


def write_probability_diagnostics(backtest_results_csv: str | Path, output_dir: str | Path, min_required_rows: int = 1) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    df = enrich_prediction_frame(load_results(backtest_results_csv))
    summary = _summary(df, min_required_rows)
    bins = pd.DataFrame([
        {"bin": "top_edge_under_0_03", "count": summary["top_edge_under_0_03_count"]},
        {"bin": "top_edge_under_0_05", "count": summary["top_edge_under_0_05_count"]},
        {"bin": "top_edge_under_0_07", "count": summary["top_edge_under_0_07_count"]},
        {"bin": "top_edge_over_0_07", "count": summary["top_edge_over_0_07_count"]},
        {"bin": "top_edge_over_0_10", "count": summary["top_edge_over_0_10_count"]},
        {"bin": "top_edge_over_0_12", "count": summary["top_edge_over_0_12_count"]},
    ])
    md = out / "probability_distribution_diagnostics.md"
    js = out / "probability_distribution_diagnostics.json"
    csv = out / "probability_distribution_bins.csv"
    js.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    bins.to_csv(csv, index=False)
    body = "no probability rows available\n" if summary["diagnostics_status"] == "EMPTY_DATASET" else "\n".join(f"- {k}: {v}" for k, v in summary.items())
    md.write_text("# v2.4 Probability Distribution Diagnostics\n\n" + body, encoding="utf-8")
    return {"probability_diagnostics_status": summary["diagnostics_status"], "probability_distribution_diagnostics_path": str(md.resolve()), "probability_distribution_json_path": str(js.resolve()), "probability_distribution_bins_path": str(csv.resolve()), **summary}


def _summary(df: pd.DataFrame, min_required_rows: int) -> dict[str, object]:
    if df.empty:
        values = {key: None for key in ["average_home_probability", "average_draw_probability", "average_away_probability", "average_top_probability", "average_top_edge", "median_top_edge", "p75_top_edge", "p90_top_edge", "probability_entropy_avg", "flat_probability_rate", "confidence_avg", "confidence_median", "confidence_p75", "confidence_p90", "confidence_cap_rate", "results_only_rate", "xg_missing_rate", "odds_missing_rate"]}
        values.update({key: 0 for key in ["top_edge_under_0_03_count", "top_edge_under_0_05_count", "top_edge_under_0_07_count", "top_edge_over_0_07_count", "top_edge_over_0_10_count", "top_edge_over_0_12_count"]})
        return {"diagnostics_status": "EMPTY_DATASET", "probability_rows_count": 0, "sample_warning": True, "min_required_rows": min_required_rows, **values}
    edge = df["top_edge"].astype(float)
    confidence = df["confidence"].astype(float)
    status = "INSUFFICIENT_SAMPLE" if len(df) < min_required_rows else "PASSED"
    return {
        "diagnostics_status": status,
        "probability_rows_count": int(len(df)),
        "sample_warning": bool(len(df) < min_required_rows),
        "min_required_rows": int(min_required_rows),
        "average_home_probability": round(float(df["home_win_probability"].mean()), 4),
        "average_draw_probability": round(float(df["draw_probability"].mean()), 4),
        "average_away_probability": round(float(df["away_win_probability"].mean()), 4),
        "average_top_probability": round(float(df["top_probability"].mean()), 4),
        "average_top_edge": round(float(edge.mean()), 4),
        "median_top_edge": round(float(edge.median()), 4),
        "p75_top_edge": round(float(edge.quantile(0.75)), 4),
        "p90_top_edge": round(float(edge.quantile(0.90)), 4),
        "probability_entropy_avg": round(float(df["probability_entropy"].mean()), 4),
        "flat_probability_rate": round(float((edge < 0.03).mean()), 4),
        "top_edge_under_0_03_count": int((edge < 0.03).sum()),
        "top_edge_under_0_05_count": int((edge < 0.05).sum()),
        "top_edge_under_0_07_count": int((edge < 0.07).sum()),
        "top_edge_over_0_07_count": int((edge >= 0.07).sum()),
        "top_edge_over_0_10_count": int((edge >= 0.10).sum()),
        "top_edge_over_0_12_count": int((edge >= 0.12).sum()),
        "confidence_avg": round(float(confidence.mean()), 4),
        "confidence_median": round(float(confidence.median()), 4),
        "confidence_p75": round(float(confidence.quantile(0.75)), 4),
        "confidence_p90": round(float(confidence.quantile(0.90)), 4),
        "confidence_cap_rate": round(float(df["confidence_cap_applied"].astype(bool).mean()), 4),
        "results_only_rate": round(float(df["prediction_tier"].astype(str).eq("TIER_2_RESULTS_ONLY").mean()), 4),
        "xg_missing_rate": round(float((~df["xg_available"].astype(bool)).mean()), 4),
        "odds_missing_rate": round(float((~df["odds_available"].astype(bool)).mean()), 4),
    }
