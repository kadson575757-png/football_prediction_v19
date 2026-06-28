# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v24_metrics import enrich_prediction_frame, load_results


def classify_no_decision(row: dict[str, object] | pd.Series, *, lean_edge: float = 0.045, lean_confidence: float = 0.50, pick_edge: float = 0.10, pick_confidence: float = 0.64) -> dict[str, object]:
    data = dict(row)
    edge = float(data.get("top_edge", 0) or 0)
    confidence = float(data.get("confidence", 0) or 0)
    reasons: list[str] = []
    if edge < lean_edge:
        reasons.append("EDGE_TOO_SMALL")
    if confidence < lean_confidence:
        reasons.append("CONFIDENCE_TOO_LOW")
    if str(data.get("source_quality_band", "")).upper() == "LOW":
        reasons.append("SOURCE_QUALITY_TOO_LOW")
    if data.get("no_xg_partial_model") or str(data.get("prediction_tier", "")) == "TIER_2_RESULTS_ONLY":
        reasons.append("RESULTS_ONLY_CONFIDENCE_CAP")
        reasons.append("MISSING_XG_CAP")
    if data.get("early_season_risk"):
        reasons.append("EARLY_SEASON_RISK")
    if float(data.get("top_probability", 0) or 0) < 0.38:
        reasons.append("PROBABILITIES_TOO_FLAT")
    if float(data.get("draw_probability", 0) or 0) >= 0.34:
        reasons.append("DRAW_RISK_TOO_HIGH")
    if not data.get("odds_available", False):
        reasons.append("MISSING_ODDS_PENALTY")
    if str(data.get("eligibility_class", "")) == "LEAN_ONLY":
        reasons.append("ELIGIBILITY_LEAN_ONLY_CAP")
    if str(data.get("model_status", "")) == "WINNER_MODEL_PARTIAL":
        reasons.append("MODEL_STATUS_PARTIAL")
    if not reasons:
        reasons.append("THRESHOLD_NOT_MET")
    return {
        "primary_reason": reasons[0] if reasons else "UNKNOWN_NO_DECISION_REASON",
        "secondary_reasons": ";".join(reasons[1:]),
        "threshold_failed": edge < lean_edge or confidence < lean_confidence,
        "actual_top_edge": edge,
        "required_top_edge": lean_edge,
        "actual_confidence": confidence,
        "required_confidence": lean_confidence,
        "nearest_decision_class": "WINNER_LEAN",
        "distance_to_winner_lean": max(0.0, lean_edge - edge) + max(0.0, lean_confidence - confidence),
        "distance_to_winner_pick": max(0.0, pick_edge - edge) + max(0.0, pick_confidence - confidence),
    }


def write_no_decision_diagnostics(backtest_results_csv: str | Path, output_dir: str | Path) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    enriched = enrich_prediction_frame(load_results(backtest_results_csv))
    no_decisions = enriched[enriched["decision_class"].astype(str).eq("NO_DECISION")].copy() if not enriched.empty else pd.DataFrame()
    rows = []
    for _, row in no_decisions.iterrows():
        rows.append({**row.to_dict(), **classify_no_decision(row)})
    result = pd.DataFrame(rows)
    csv_path = out / "no_decision_diagnostics.csv"
    json_path = out / "no_decision_diagnostics.json"
    report_path = out / "no_decision_diagnostics_report.md"
    result.to_csv(csv_path, index=False)
    json_path.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")
    report_path.write_text("# v2.4 NO_DECISION Diagnostics\n\n" + (result["primary_reason"].value_counts().to_csv() if not result.empty else "No NO_DECISION rows.\n"), encoding="utf-8")
    return {"no_decision_diagnostics_status": "PASSED", "no_decision_diagnostics_csv_path": str(csv_path.resolve()), "no_decision_diagnostics_json_path": str(json_path.resolve()), "no_decision_diagnostics_report_path": str(report_path.resolve()), "unknown_reason_count": int(result["primary_reason"].eq("UNKNOWN_NO_DECISION_REASON").sum()) if not result.empty else 0}
