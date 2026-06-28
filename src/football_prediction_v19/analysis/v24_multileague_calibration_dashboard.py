# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v24_metrics import enrich_prediction_frame, load_results
from football_prediction_v19.analysis.v24_no_decision_diagnostics import classify_no_decision


def write_multileague_calibration_dashboard(backtest_results_csv: str | Path, output_dir: str | Path) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    df = enrich_prediction_frame(load_results(backtest_results_csv))
    rows = []
    reason_rows = []
    for league, group in df.groupby("competition") if not df.empty else []:
        decisions = group[group["decision_class"].isin(["WINNER_PICK", "WINNER_LEAN"])]
        no_decisions = group[group["decision_class"].eq("NO_DECISION")]
        reasons = [classify_no_decision(row)["primary_reason"] for _, row in no_decisions.iterrows()]
        main_reason = pd.Series(reasons).mode().iloc[0] if reasons else ""
        rows.append({
            "competition": league,
            "matches_evaluated": len(group),
            "xg_available_rate": round(float(group["xg_available"].astype(bool).mean()), 4),
            "odds_available_rate": round(float(group["odds_available"].astype(bool).mean()), 4),
            "results_only_rate": round(float(group["prediction_tier"].eq("TIER_2_RESULTS_ONLY").mean()), 4),
            "model_ran_count": int(group["model_status"].ne("WINNER_MODEL_BLOCKED").sum()),
            "probabilities_created_count": int(group["top_probability"].gt(0).sum()),
            "winner_pick_count": int(group["decision_class"].eq("WINNER_PICK").sum()),
            "winner_lean_count": int(group["decision_class"].eq("WINNER_LEAN").sum()),
            "no_decision_count": int(group["decision_class"].eq("NO_DECISION").sum()),
            "decision_coverage_rate": round(float(len(decisions) / len(group)), 4) if len(group) else 0.0,
            "top1_accuracy_all_outputs": round(float(group["top1_correct"].mean()), 4),
            "top1_accuracy_decisions_only": round(float(decisions["top1_correct"].mean()), 4) if not decisions.empty else 0.0,
            "brier_score_all": round(float(group["brier_score_row"].mean()), 4),
            "brier_score_decisions_only": round(float(decisions["brier_score_row"].mean()), 4) if not decisions.empty else 0.0,
            "average_top_edge": round(float(group["top_edge"].mean()), 4),
            "median_top_edge": round(float(group["top_edge"].median()), 4),
            "main_no_decision_reason": main_reason,
        })
        for reason in reasons:
            reason_rows.append({"competition": league, "primary_reason": reason})
    summary = pd.DataFrame(rows)
    reasons_frame = pd.DataFrame(reason_rows)
    summary.to_csv(out / "multileague_calibration_summary.csv", index=False)
    summary[["competition", "decision_coverage_rate", "winner_pick_count", "winner_lean_count", "no_decision_count"]].to_csv(out / "league_decision_coverage.csv", index=False)
    summary[["competition", "average_top_edge", "median_top_edge", "xg_available_rate", "odds_available_rate"]].to_csv(out / "league_probability_diagnostics.csv", index=False)
    summary.to_csv(out / "league_threshold_simulation.csv", index=False)
    reasons_frame.to_csv(out / "league_no_decision_reasons.csv", index=False)
    (out / "multileague_calibration_dashboard.md").write_text("# v2.4 Multileague Calibration Dashboard\n\n" + summary.to_csv(index=False), encoding="utf-8")
    return {"multileague_calibration_status": "PASSED", "multileague_calibration_dashboard_path": str((out / "multileague_calibration_dashboard.md").resolve()), "multileague_calibration_summary_path": str((out / "multileague_calibration_summary.csv").resolve())}
