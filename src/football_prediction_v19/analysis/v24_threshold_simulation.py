# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v24_metrics import enrich_prediction_frame, load_results


POLICIES = {
    "conservative": {"pick_edge": 0.12, "pick_conf": 0.68, "lean_edge": 0.07, "lean_conf": 0.55, "pick_results_only": False},
    "balanced": {"pick_edge": 0.10, "pick_conf": 0.64, "lean_edge": 0.05, "lean_conf": 0.52, "pick_results_only": False},
    "results_only_balanced": {"pick_edge": 9.0, "pick_conf": 9.0, "lean_edge": 0.045, "lean_conf": 0.50, "pick_results_only": False},
    "xg_full_model": {"pick_edge": 0.10, "pick_conf": 0.62, "lean_edge": 0.055, "lean_conf": 0.52, "pick_results_only": False},
    "exploratory_low_coverage": {"pick_edge": 9.0, "pick_conf": 9.0, "lean_edge": 0.035, "lean_conf": 0.48, "pick_results_only": False},
}


def write_threshold_simulation(backtest_results_csv: str | Path, output_dir: str | Path) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    df = enrich_prediction_frame(load_results(backtest_results_csv))
    rows = [_simulate_policy(name, policy, df) for name, policy in POLICIES.items()]
    result = pd.DataFrame(rows)
    csv = out / "threshold_simulation_results.csv"
    md = out / "threshold_simulation_report.md"
    js = out / "threshold_policy_comparison.json"
    result.to_csv(csv, index=False)
    js.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    md.write_text("# v2.4 Threshold Simulation\n\n" + result.to_csv(index=False) + "\nNo ROI. No stake. No profit.\n", encoding="utf-8")
    selected = result[result["policy_name"].eq("results_only_balanced")]
    selected_row = selected.iloc[0].to_dict() if not selected.empty else {}
    return {"threshold_simulation_status": "PASSED", "threshold_simulation_results_path": str(csv.resolve()), "threshold_simulation_report_path": str(md.resolve()), "threshold_policy_comparison_path": str(js.resolve()), "selected_policy_top1_accuracy_decisions_only": selected_row.get("top1_accuracy_decisions_only", 0), "selected_policy_brier_score_decisions_only": selected_row.get("brier_score_decisions_only", 0)}


def _simulate_policy(name: str, policy: dict[str, float | bool], df: pd.DataFrame) -> dict[str, object]:
    decisions = []
    for _, row in df.iterrows():
        results_only = row["prediction_tier"] == "TIER_2_RESULTS_ONLY" or bool(row["no_xg_partial_model"])
        if row["top_edge"] >= policy["pick_edge"] and row["confidence"] >= policy["pick_conf"] and (not results_only or policy["pick_results_only"]):
            decision = "WINNER_PICK"
        elif row["top_edge"] >= policy["lean_edge"] and row["confidence"] >= policy["lean_conf"]:
            decision = "WINNER_LEAN"
        else:
            decision = "NO_DECISION"
        decisions.append(decision)
    if df.empty:
        return {"policy_name": name, "matches_evaluated": 0, "decision_coverage_rate": 0, "winner_pick_count": 0, "winner_lean_count": 0, "no_decision_count": 0, "top1_accuracy_all_model_outputs": 0, "top1_accuracy_decisions_only": 0, "brier_score_all": 0, "brier_score_decisions_only": 0, "average_confidence_decisions": 0, "average_top_edge_decisions": 0, "correct_count": 0, "incorrect_count": 0, "draw_result_error_count": 0, "home_bias_rate": 0, "away_bias_rate": 0, "draw_prediction_rate": 0}
    sim = df.copy()
    sim["simulated_decision"] = decisions
    decision_rows = sim[sim["simulated_decision"].isin(["WINNER_PICK", "WINNER_LEAN"])]
    correct = int(decision_rows["top1_correct"].sum()) if not decision_rows.empty else 0
    return {
        "policy_name": name,
        "matches_evaluated": int(len(sim)),
        "decision_coverage_rate": round(float(len(decision_rows) / len(sim)), 4),
        "winner_pick_count": int((sim["simulated_decision"] == "WINNER_PICK").sum()),
        "winner_lean_count": int((sim["simulated_decision"] == "WINNER_LEAN").sum()),
        "no_decision_count": int((sim["simulated_decision"] == "NO_DECISION").sum()),
        "top1_accuracy_all_model_outputs": round(float(sim["top1_correct"].mean()), 4),
        "top1_accuracy_decisions_only": round(correct / len(decision_rows), 4) if not decision_rows.empty else 0.0,
        "brier_score_all": round(float(sim["brier_score_row"].mean()), 4),
        "brier_score_decisions_only": round(float(decision_rows["brier_score_row"].mean()), 4) if not decision_rows.empty else 0.0,
        "average_confidence_decisions": round(float(decision_rows["confidence"].mean()), 4) if not decision_rows.empty else 0.0,
        "average_top_edge_decisions": round(float(decision_rows["top_edge"].mean()), 4) if not decision_rows.empty else 0.0,
        "correct_count": correct,
        "incorrect_count": int(len(decision_rows) - correct),
        "draw_result_error_count": int(((decision_rows["result_1x2"] == "D") & (~decision_rows["top1_correct"])).sum()) if not decision_rows.empty else 0,
        "home_bias_rate": round(float((decision_rows["predicted_top_class"] == "HOME").mean()), 4) if not decision_rows.empty else 0.0,
        "away_bias_rate": round(float((decision_rows["predicted_top_class"] == "AWAY").mean()), 4) if not decision_rows.empty else 0.0,
        "draw_prediction_rate": round(float((decision_rows["predicted_top_class"] == "DRAW").mean()), 4) if not decision_rows.empty else 0.0,
    }
