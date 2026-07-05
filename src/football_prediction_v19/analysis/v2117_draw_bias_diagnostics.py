# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

OUTCOMES = ["HOME", "DRAW", "AWAY"]
THRESHOLDS = [0.28, 0.30, 0.32, 0.34, 0.36]
LIFT_RULES = [
    ("DRAW_LIFT_A_028_GAP_003", 0.28, 0.03),
    ("DRAW_LIFT_B_028_GAP_005", 0.28, 0.05),
    ("DRAW_LIFT_C_030_GAP_005", 0.30, 0.05),
    ("DRAW_LIFT_D_032_GAP_006", 0.32, 0.06),
]


def analyze_draw_bias(
    rows: pd.DataFrame,
    *,
    output_dir: str | Path = "outputs/v2117_draw_bias_diagnostics",
    min_draw_probability: float = 0.28,
    near_draw_edge: float = 0.05,
) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    prepared = prepare_draw_rows(rows)
    prepared = add_draw_rank(prepared)
    prepared = add_near_draw_candidates(prepared, min_draw_probability=min_draw_probability, near_draw_edge=near_draw_edge)
    evaluable = prepared[prepared["actual_result"].isin(OUTCOMES) & prepared["top_probability_outcome"].isin(OUTCOMES)].copy()
    missed = evaluable[evaluable["actual_result"].eq("DRAW") & ~evaluable["top_probability_outcome"].eq("DRAW")].copy()
    threshold_probe = compute_threshold_probe(evaluable, thresholds=THRESHOLDS)
    lift_rules = compute_draw_lift_rules(evaluable)
    groups = {
        "edge_band": compute_group_analysis(evaluable, "probability_edge_band"),
        "uncertainty": compute_group_analysis(evaluable, "uncertainty_level"),
        "data_quality": compute_group_analysis(evaluable, "data_quality_band"),
    }
    summary = compute_summary(evaluable, prepared, threshold_probe, lift_rules, output_dir=out)
    missed = missed.sort_values("draw_gap_to_top", ascending=True)
    missed[_missed_columns(missed)].to_csv(out / "v2117_missed_draw_rows.csv", index=False)
    threshold_probe.to_csv(out / "v2117_draw_threshold_probe.csv", index=False)
    lift_rules.to_csv(out / "v2117_draw_lift_candidate_rules.csv", index=False)
    groups["edge_band"].to_csv(out / "v2117_draw_by_edge_band.csv", index=False)
    groups["uncertainty"].to_csv(out / "v2117_draw_by_uncertainty.csv", index=False)
    groups["data_quality"].to_csv(out / "v2117_draw_by_data_quality.csv", index=False)
    (out / "v2117_draw_bias_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    (out / "v2117_draw_bias_report.md").write_text(render_report(summary, threshold_probe, lift_rules), encoding="utf-8")
    return {
        **summary,
        "missed_draw_rows_csv_path": str((out / "v2117_missed_draw_rows.csv").resolve()),
        "threshold_probe_csv_path": str((out / "v2117_draw_threshold_probe.csv").resolve()),
        "lift_rules_csv_path": str((out / "v2117_draw_lift_candidate_rules.csv").resolve()),
        "summary_json_path": str((out / "v2117_draw_bias_summary.json").resolve()),
        "report_md_path": str((out / "v2117_draw_bias_report.md").resolve()),
    }


def prepare_draw_rows(rows: pd.DataFrame) -> pd.DataFrame:
    frame = rows.copy()
    mapping = {
        "match_date": ["match_date", "Date"],
        "home_team": ["home_team", "HomeTeam"],
        "away_team": ["away_team", "AwayTeam"],
        "actual_result": ["actual_result", "actual_result_outcome"],
        "top_probability_outcome": ["top_probability_outcome", "top_outcome"],
        "home_win_probability": ["home_win_probability", "home_probability"],
        "draw_probability": ["draw_probability"],
        "away_win_probability": ["away_win_probability", "away_probability"],
        "probability_edge": ["probability_edge"],
        "probability_edge_band": ["probability_edge_band"],
        "uncertainty_level": ["uncertainty_level"],
        "data_quality_band": ["data_quality_band"],
    }
    out = pd.DataFrame(index=frame.index)
    for target, candidates in mapping.items():
        source = next((col for col in candidates if col in frame.columns), None)
        out[target] = frame[source] if source else ""
    for col in ["home_win_probability", "draw_probability", "away_win_probability", "probability_edge"]:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)
    out["actual_result"] = out["actual_result"].astype(str).str.upper()
    out["top_probability_outcome"] = out["top_probability_outcome"].astype(str).str.upper()
    return out


def add_draw_rank(rows: pd.DataFrame) -> pd.DataFrame:
    frame = rows.copy()
    ranks = []
    gaps = []
    for _, row in frame.iterrows():
        probs = {
            "HOME": float(row.get("home_win_probability", 0.0)),
            "DRAW": float(row.get("draw_probability", 0.0)),
            "AWAY": float(row.get("away_win_probability", 0.0)),
        }
        draw = probs["DRAW"]
        top = max(probs.values())
        rank = 1 + sum(value > draw for value in probs.values())
        ranks.append(int(rank))
        gaps.append(round(top - draw, 4))
    frame["draw_rank"] = ranks
    frame["draw_gap_to_top"] = gaps
    return frame


def add_near_draw_candidates(rows: pd.DataFrame, *, min_draw_probability: float = 0.28, near_draw_edge: float = 0.05) -> pd.DataFrame:
    frame = rows.copy()
    frame["near_draw_candidate"] = frame["draw_probability"].ge(min_draw_probability) & frame["draw_gap_to_top"].le(near_draw_edge)
    return frame


def compute_threshold_probe(rows: pd.DataFrame, *, thresholds: list[float] | None = None) -> pd.DataFrame:
    thresholds = thresholds or THRESHOLDS
    actual_draw_total = int(rows["actual_result"].eq("DRAW").sum()) if not rows.empty else 0
    records = []
    for threshold in thresholds:
        subset = rows[rows["draw_probability"].ge(threshold)] if not rows.empty else pd.DataFrame()
        actual_draw_count = int(subset["actual_result"].eq("DRAW").sum()) if not subset.empty else 0
        candidate_count = int(len(subset))
        records.append({
            "threshold": threshold,
            "candidate_count": candidate_count,
            "actual_draw_count": actual_draw_count,
            "false_draw_count": candidate_count - actual_draw_count,
            "precision": _rate(actual_draw_count, candidate_count),
            "recall": _rate(actual_draw_count, actual_draw_total),
        })
    return pd.DataFrame(records)


def compute_draw_lift_rules(rows: pd.DataFrame) -> pd.DataFrame:
    baseline_hits = int(rows["top_probability_outcome"].eq(rows["actual_result"]).sum()) if not rows.empty else 0
    baseline_rate = _rate(baseline_hits, len(rows))
    actual_draw_total = int(rows["actual_result"].eq("DRAW").sum()) if not rows.empty else 0
    records = []
    for name, min_prob, max_gap in LIFT_RULES:
        candidates = rows["draw_probability"].ge(min_prob) & rows["draw_gap_to_top"].le(max_gap) if not rows.empty else pd.Series(dtype=bool)
        adjusted = rows["top_probability_outcome"].copy() if not rows.empty else pd.Series(dtype=str)
        adjusted.loc[candidates] = "DRAW"
        hits = int(adjusted.eq(rows["actual_result"]).sum()) if not rows.empty else 0
        candidate_count = int(candidates.sum()) if not rows.empty else 0
        actual_draw_count = int((candidates & rows["actual_result"].eq("DRAW")).sum()) if not rows.empty else 0
        hypothetical_rate = _rate(hits, len(rows))
        records.append({
            "rule_name": name,
            "candidate_count": candidate_count,
            "actual_draw_count": actual_draw_count,
            "false_draw_count": candidate_count - actual_draw_count,
            "precision": _rate(actual_draw_count, candidate_count),
            "recall": _rate(actual_draw_count, actual_draw_total),
            "hypothetical_top_hit_rate": hypothetical_rate,
            "delta_vs_baseline_top_hit_rate": round(hypothetical_rate - baseline_rate, 4),
        })
    return pd.DataFrame(records)


def compute_group_analysis(rows: pd.DataFrame, column: str) -> pd.DataFrame:
    if rows.empty or column not in rows.columns:
        return pd.DataFrame(columns=[column, "count", "actual_draw_count", "actual_draw_rate", "predicted_draw_top_count", "missed_draw_count", "average_draw_probability", "near_draw_candidate_count", "near_draw_precision", "near_draw_recall"])
    records = []
    total_draws = int(rows["actual_result"].eq("DRAW").sum())
    for value, group in rows.groupby(column, dropna=False):
        actual_draw_count = int(group["actual_result"].eq("DRAW").sum())
        near = group[group["near_draw_candidate"].astype(bool)]
        near_draw_hits = int(near["actual_result"].eq("DRAW").sum()) if not near.empty else 0
        records.append({
            column: value,
            "count": int(len(group)),
            "actual_draw_count": actual_draw_count,
            "actual_draw_rate": _rate(actual_draw_count, len(group)),
            "predicted_draw_top_count": int(group["top_probability_outcome"].eq("DRAW").sum()),
            "missed_draw_count": int(group["actual_result"].eq("DRAW").sum() - ((group["actual_result"].eq("DRAW")) & (group["top_probability_outcome"].eq("DRAW"))).sum()),
            "average_draw_probability": round(float(group["draw_probability"].mean()), 4) if not group.empty else 0.0,
            "near_draw_candidate_count": int(len(near)),
            "near_draw_precision": _rate(near_draw_hits, len(near)),
            "near_draw_recall": _rate(near_draw_hits, total_draws),
        })
    return pd.DataFrame(records)


def compute_summary(prepared: pd.DataFrame, all_rows: pd.DataFrame, threshold_probe: pd.DataFrame, lift_rules: pd.DataFrame, *, output_dir: Path) -> dict[str, object]:
    actual_draws = prepared[prepared["actual_result"].eq("DRAW")]
    non_draws = prepared[prepared["actual_result"].isin(["HOME", "AWAY"])]
    baseline_hits = int(prepared["top_probability_outcome"].eq(prepared["actual_result"]).sum()) if not prepared.empty else 0
    predicted_draw_top = int(prepared["top_probability_outcome"].eq("DRAW").sum()) if not prepared.empty else 0
    draw_top_hits = int((prepared["top_probability_outcome"].eq("DRAW") & prepared["actual_result"].eq("DRAW")).sum()) if not prepared.empty else 0
    missed_draw_count = int((prepared["actual_result"].eq("DRAW") & ~prepared["top_probability_outcome"].eq("DRAW")).sum()) if not prepared.empty else 0
    near = prepared[prepared["near_draw_candidate"].astype(bool)] if "near_draw_candidate" in prepared.columns else pd.DataFrame()
    near_hits = int(near["actual_result"].eq("DRAW").sum()) if not near.empty else 0
    best = best_draw_lift_rule(lift_rules)
    avg_actual = _mean(actual_draws["draw_probability"])
    avg_non = _mean(non_draws["draw_probability"])
    summary = {
        "v2117_draw_bias_diagnostics_status": "READY",
        "rows_loaded": int(len(all_rows)),
        "evaluable_count": int(len(prepared)),
        "baseline_top_probability_hit_rate": _rate(baseline_hits, len(prepared)),
        "actual_draw_count": int(len(actual_draws)),
        "actual_draw_rate": _rate(len(actual_draws), len(prepared)),
        "predicted_draw_top_count": predicted_draw_top,
        "predicted_draw_top_rate": _rate(predicted_draw_top, len(prepared)),
        "draw_top_hit_rate": _rate(draw_top_hits, predicted_draw_top),
        "missed_draw_count": missed_draw_count,
        "missed_draw_rate": _rate(missed_draw_count, len(actual_draws)),
        "average_draw_probability_on_actual_draws": avg_actual,
        "median_draw_probability_on_actual_draws": _median(actual_draws["draw_probability"]),
        "max_draw_probability_on_actual_draws": _max(actual_draws["draw_probability"]),
        "min_draw_probability_on_actual_draws": _min(actual_draws["draw_probability"]),
        "average_draw_probability_on_non_draws": avg_non,
        "median_draw_probability_on_non_draws": _median(non_draws["draw_probability"]),
        "actual_draw_probability_gap": round(avg_actual - avg_non, 4),
        "actual_draw_rank_1_count": int(actual_draws["draw_rank"].eq(1).sum()) if not actual_draws.empty else 0,
        "actual_draw_rank_2_count": int(actual_draws["draw_rank"].eq(2).sum()) if not actual_draws.empty else 0,
        "actual_draw_rank_3_count": int(actual_draws["draw_rank"].eq(3).sum()) if not actual_draws.empty else 0,
        "actual_draw_rank_1_rate": _rate(int(actual_draws["draw_rank"].eq(1).sum()) if not actual_draws.empty else 0, len(actual_draws)),
        "actual_draw_rank_2_rate": _rate(int(actual_draws["draw_rank"].eq(2).sum()) if not actual_draws.empty else 0, len(actual_draws)),
        "actual_draw_rank_3_rate": _rate(int(actual_draws["draw_rank"].eq(3).sum()) if not actual_draws.empty else 0, len(actual_draws)),
        "near_draw_candidate_count": int(len(near)),
        "near_draw_actual_draw_count": near_hits,
        "near_draw_hit_rate": _rate(near_hits, len(near)),
        "near_draw_precision": _rate(near_hits, len(near)),
        "near_draw_recall": _rate(near_hits, len(actual_draws)),
        "near_draw_home_top_count": int(near["top_probability_outcome"].eq("HOME").sum()) if not near.empty else 0,
        "near_draw_away_top_count": int(near["top_probability_outcome"].eq("AWAY").sum()) if not near.empty else 0,
        "best_draw_lift_rule": best.get("rule_name", ""),
        "best_draw_lift_rule_precision": float(best.get("precision", 0.0)),
        "best_draw_lift_rule_recall": float(best.get("recall", 0.0)),
        "best_draw_lift_rule_hypothetical_top_hit_rate": float(best.get("hypothetical_top_hit_rate", 0.0)),
        "best_draw_lift_rule_delta_vs_baseline": float(best.get("delta_vs_baseline_top_hit_rate", 0.0)),
        "output_dir": str(output_dir),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }
    summary["main_draw_problem"] = classify_main_draw_problem(summary)
    summary["recommendation"] = recommendation(summary)
    return summary


def best_draw_lift_rule(lift_rules: pd.DataFrame) -> dict[str, object]:
    if lift_rules.empty:
        return {}
    ranked = lift_rules.sort_values(["hypothetical_top_hit_rate", "precision", "candidate_count"], ascending=[False, False, False])
    return ranked.iloc[0].to_dict()


def classify_main_draw_problem(summary: dict[str, object]) -> str:
    if int(summary.get("predicted_draw_top_count", 0)) == 0 and int(summary.get("actual_draw_count", 0)) > 0:
        return "DRAW_NEVER_TOP"
    if float(summary.get("actual_draw_probability_gap", 0.0)) <= 0:
        return "DRAW_SIGNAL_NOT_INFORMATIVE"
    if float(summary.get("actual_draw_rank_2_rate", 0.0)) >= 0.5:
        return "DRAW_OFTEN_RANK_2"
    if float(summary.get("average_draw_probability_on_actual_draws", 0.0)) < 0.28:
        return "DRAW_TOO_LOW_ON_ACTUAL_DRAWS"
    return "DRAW_THRESHOLD_TOO_CONSERVATIVE"


def recommendation(summary: dict[str, object]) -> str:
    delta = float(summary.get("best_draw_lift_rule_delta_vs_baseline", 0.0))
    precision = float(summary.get("best_draw_lift_rule_precision", 0.0))
    if summary.get("main_draw_problem") == "DRAW_SIGNAL_NOT_INFORMATIVE":
        return "DRAW_PROBABILITY_NOT_INFORMATIVE"
    if delta > 0 and precision >= 0.35:
        return "DRAW_LIFT_PROMISING"
    if delta > 0:
        return "DRAW_LIFT_LOW_PRECISION"
    return "KEEP_AS_DIAGNOSTIC_ONLY"


def render_report(summary: dict[str, object], threshold_probe: pd.DataFrame, lift_rules: pd.DataFrame) -> str:
    return "\n".join([
        "# v2.11.7 Draw Bias Diagnostics",
        "",
        "## Summary",
        f"- rows_loaded: {summary['rows_loaded']}",
        f"- evaluable_count: {summary['evaluable_count']}",
        f"- baseline_top_probability_hit_rate: {summary['baseline_top_probability_hit_rate']}",
        "",
        "## Actual Draw Rate vs Predicted Draw Top Rate",
        f"- actual_draw_rate: {summary['actual_draw_rate']}",
        f"- predicted_draw_top_rate: {summary['predicted_draw_top_rate']}",
        "",
        "## Draw Probability on Actual Draws",
        f"- average_draw_probability_on_actual_draws: {summary['average_draw_probability_on_actual_draws']}",
        f"- average_draw_probability_on_non_draws: {summary['average_draw_probability_on_non_draws']}",
        "",
        "## Draw Rank Analysis",
        f"- actual_draw_rank_1_rate: {summary['actual_draw_rank_1_rate']}",
        f"- actual_draw_rank_2_rate: {summary['actual_draw_rank_2_rate']}",
        f"- actual_draw_rank_3_rate: {summary['actual_draw_rank_3_rate']}",
        "",
        "## Near-Draw Candidates",
        f"- near_draw_candidate_count: {summary['near_draw_candidate_count']}",
        f"- near_draw_precision: {summary['near_draw_precision']}",
        f"- near_draw_recall: {summary['near_draw_recall']}",
        "",
        "## Missed Draws",
        f"- missed_draw_count: {summary['missed_draw_count']}",
        "",
        "## Threshold Probe",
        _markdown_table(threshold_probe),
        "",
        "## Hypothetical Draw-Lift Rules",
        _markdown_table(lift_rules),
        "",
        "## Group Analysis",
        "Group CSV files are written for edge band, uncertainty, and data quality.",
        "",
        "## Recommendation",
        f"- main_draw_problem: {summary['main_draw_problem']}",
        f"- recommendation: {summary['recommendation']}",
        "",
        "Safety: automatic_betting_enabled=false, staking_logic_enabled=false, roi_logic_enabled=false.",
    ])


def _missed_columns(frame: pd.DataFrame) -> list[str]:
    cols = [
        "match_date", "home_team", "away_team", "actual_result", "top_probability_outcome",
        "home_win_probability", "draw_probability", "away_win_probability", "draw_rank",
        "draw_gap_to_top", "probability_edge", "probability_edge_band", "uncertainty_level",
        "data_quality_band",
    ]
    return [col for col in cols if col in frame.columns]


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return ""
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in cols) + " |")
    return "\n".join(lines)


def _rate(count: int, total: int) -> float:
    return round(float(count / total), 4) if total else 0.0


def _mean(series: pd.Series) -> float:
    return round(float(series.mean()), 4) if len(series) else 0.0


def _median(series: pd.Series) -> float:
    return round(float(series.median()), 4) if len(series) else 0.0


def _max(series: pd.Series) -> float:
    return round(float(series.max()), 4) if len(series) else 0.0


def _min(series: pd.Series) -> float:
    return round(float(series.min()), 4) if len(series) else 0.0
