# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v24_metrics import enrich_prediction_frame, load_results


BINS = [(0.00, 0.40), (0.40, 0.50), (0.50, 0.55), (0.55, 0.60), (0.60, 0.65), (0.65, 0.70), (0.70, 1.00)]


def write_confidence_calibration(backtest_results_csv: str | Path, output_dir: str | Path, min_required_rows: int = 1) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    df = enrich_prediction_frame(load_results(backtest_results_csv))
    rows = []
    for low, high in BINS:
        group = df[(df["confidence"] >= low) & (df["confidence"] < high if high < 1 else df["confidence"] <= high)] if not df.empty else pd.DataFrame()
        rows.append({
            "confidence_bin": f"{low:.2f}-{high:.2f}",
            "count": int(len(group)),
            "average_confidence": round(float(group["confidence"].mean()), 4) if not group.empty else 0.0,
            "top1_accuracy": round(float(group["top1_correct"].mean()), 4) if not group.empty else 0.0,
            "average_brier": round(float(group["brier_score_row"].mean()), 4) if not group.empty else 0.0,
            "average_top_edge": round(float(group["top_edge"].mean()), 4) if not group.empty else 0.0,
            "decision_count": int(group["decision_class"].isin(["WINNER_PICK", "WINNER_LEAN"]).sum()) if not group.empty else 0,
            "no_decision_count": int(group["decision_class"].eq("NO_DECISION").sum()) if not group.empty else 0,
            "xg_available_rate": round(float(group["xg_available"].astype(bool).mean()), 4) if not group.empty else 0.0,
            "results_only_rate": round(float(group["prediction_tier"].eq("TIER_2_RESULTS_ONLY").mean()), 4) if not group.empty else 0.0,
        })
    bins = pd.DataFrame(rows)
    csv = out / "confidence_calibration_bins.csv"
    md = out / "confidence_calibration_report.md"
    js = out / "confidence_calibration_summary.json"
    bins.to_csv(csv, index=False)
    total = int(len(df))
    status = "EMPTY_DATASET" if total == 0 else ("INSUFFICIENT_SAMPLE" if total < min_required_rows else "PASSED")
    summary = {"confidence_calibration_status": status, "total_rows": total, "total_count": total, "min_required_rows": int(min_required_rows), "sample_warning": bool(total < min_required_rows), "non_empty_bins": int((bins["count"] > 0).sum())}
    js.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    md.write_text("# v2.4 Confidence Calibration\n\n" + bins.to_csv(index=False), encoding="utf-8")
    return {**summary, "confidence_calibration_bins_path": str(csv.resolve()), "confidence_calibration_report_path": str(md.resolve()), "confidence_calibration_summary_path": str(js.resolve())}
