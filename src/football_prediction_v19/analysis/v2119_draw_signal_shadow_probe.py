# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

OUTCOMES = ["HOME", "DRAW", "AWAY"]
STRATEGIES = [
    "BASELINE",
    "EDGE_3_6_DRAW_TOP",
    "EDGE_0_6_DRAW_TOP",
    "EDGE_3_6_AND_DRAW_PROB_028",
    "EDGE_3_6_AND_DRAW_RANK_2",
    "EDGE_3_6_SOFT_MIX",
    "EDGE_3_6_PROTECT_HOME_AWAY",
]


def analyze_draw_signal_shadow_probe(
    rows: pd.DataFrame,
    *,
    output_dir: str | Path = "outputs/v2119_draw_signal_shadow_probe",
) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    prepared = prepare_shadow_rows(rows)
    strategy_rows = pd.concat([apply_shadow_strategy(prepared, strategy) for strategy in STRATEGIES], ignore_index=True) if not prepared.empty else pd.DataFrame()
    summary_frame = compute_strategy_summary(strategy_rows)
    summary = compute_probe_summary(prepared, summary_frame, output_dir=out)
    strategy_rows.to_csv(out / "v2119_draw_signal_shadow_rows.csv", index=False)
    summary_frame.to_csv(out / "v2119_draw_signal_shadow_strategy_summary.csv", index=False)
    (out / "v2119_draw_signal_shadow_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    (out / "v2119_draw_signal_shadow_report.md").write_text(render_report(summary, summary_frame), encoding="utf-8")
    return {
        **summary,
        "rows_csv_path": str((out / "v2119_draw_signal_shadow_rows.csv").resolve()),
        "strategy_summary_csv_path": str((out / "v2119_draw_signal_shadow_strategy_summary.csv").resolve()),
        "summary_json_path": str((out / "v2119_draw_signal_shadow_summary.json").resolve()),
        "report_md_path": str((out / "v2119_draw_signal_shadow_report.md").resolve()),
    }


def prepare_shadow_rows(rows: pd.DataFrame) -> pd.DataFrame:
    frame = rows.copy()
    out = pd.DataFrame(index=frame.index)
    for target, candidates in {
        "match_date": ["match_date", "Date"],
        "home_team": ["home_team", "HomeTeam"],
        "away_team": ["away_team", "AwayTeam"],
        "actual_result": ["actual_result", "actual_result_outcome"],
        "top_probability_outcome": ["top_probability_outcome", "top_outcome"],
        "home_win_probability": ["home_win_probability", "home_probability"],
        "draw_probability": ["draw_probability"],
        "away_win_probability": ["away_win_probability", "away_probability"],
        "probability_edge": ["probability_edge"],
    }.items():
        source = next((col for col in candidates if col in frame.columns), None)
        out[target] = frame[source] if source else ""
    for col in ["home_win_probability", "draw_probability", "away_win_probability", "probability_edge"]:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)
    out["actual_result"] = out["actual_result"].astype(str).str.upper()
    out["top_probability_outcome"] = out["top_probability_outcome"].astype(str).str.upper()
    out = out[out["actual_result"].isin(OUTCOMES) & out["top_probability_outcome"].isin(OUTCOMES)].copy()
    out["probability_edge_signal"] = out["probability_edge"].map(probability_edge_signal)
    out = add_draw_rank(out)
    return out.reset_index(drop=True)


def probability_edge_signal(edge: object) -> str:
    value = float(edge or 0.0)
    if value <= 0.03:
        return "EDGE_0_3"
    if value <= 0.06:
        return "EDGE_3_6"
    if value <= 0.10:
        return "EDGE_6_10"
    return "EDGE_GT_10"


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
        ranks.append(int(1 + sum(value > draw for value in probs.values())))
        gaps.append(round(top - draw, 4))
    frame["draw_rank"] = ranks
    frame["draw_gap_to_top"] = gaps
    return frame


def apply_shadow_strategy(rows: pd.DataFrame, strategy_name: str) -> pd.DataFrame:
    frame = rows.copy()
    frame["strategy_name"] = strategy_name
    frame["shadow_top_outcome"] = frame["top_probability_outcome"]
    if strategy_name == "EDGE_3_6_DRAW_TOP":
        mask = frame["probability_edge_signal"].eq("EDGE_3_6")
    elif strategy_name == "EDGE_0_6_DRAW_TOP":
        mask = frame["probability_edge"].le(0.06)
    elif strategy_name == "EDGE_3_6_AND_DRAW_PROB_028":
        mask = frame["probability_edge_signal"].eq("EDGE_3_6") & frame["draw_probability"].ge(0.28)
    elif strategy_name == "EDGE_3_6_AND_DRAW_RANK_2":
        mask = frame["probability_edge_signal"].eq("EDGE_3_6") & frame["draw_rank"].eq(2)
    elif strategy_name == "EDGE_3_6_SOFT_MIX":
        mask = frame["probability_edge_signal"].eq("EDGE_3_6") & frame["draw_probability"].ge(0.29) & frame["draw_gap_to_top"].le(0.08)
    elif strategy_name == "EDGE_3_6_PROTECT_HOME_AWAY":
        mask = frame["probability_edge_signal"].eq("EDGE_3_6") & frame["draw_gap_to_top"].le(0.06)
    else:
        mask = pd.Series(False, index=frame.index)
    frame.loc[mask, "shadow_top_outcome"] = "DRAW"
    frame["shadow_hit"] = frame["shadow_top_outcome"].eq(frame["actual_result"])
    frame["baseline_hit"] = frame["top_probability_outcome"].eq(frame["actual_result"])
    frame["newly_captured_draw"] = frame["actual_result"].eq("DRAW") & ~frame["baseline_hit"] & frame["shadow_hit"]
    frame["newly_created_false_draw"] = frame["shadow_top_outcome"].eq("DRAW") & ~frame["actual_result"].eq("DRAW") & frame["baseline_hit"]
    return frame


def compute_strategy_summary(strategy_rows: pd.DataFrame) -> pd.DataFrame:
    records = []
    baseline_rate = _baseline_hit_rate(strategy_rows)
    for strategy, group in strategy_rows.groupby("strategy_name", sort=False) if not strategy_rows.empty else []:
        records.append(compute_strategy_metrics(strategy, group, baseline_rate=baseline_rate))
    return pd.DataFrame(records)


def compute_strategy_metrics(strategy_name: str, group: pd.DataFrame, *, baseline_rate: float) -> dict[str, object]:
    evaluable = len(group)
    hit_count = int(group["shadow_hit"].sum()) if not group.empty else 0
    draw_predictions = group[group["shadow_top_outcome"].eq("DRAW")] if not group.empty else pd.DataFrame()
    draw_hit_count = int(draw_predictions["actual_result"].eq("DRAW").sum()) if not draw_predictions.empty else 0
    actual_draw_count = int(group["actual_result"].eq("DRAW").sum()) if not group.empty else 0
    home_rows = group[group["actual_result"].eq("HOME")] if not group.empty else pd.DataFrame()
    away_rows = group[group["actual_result"].eq("AWAY")] if not group.empty else pd.DataFrame()
    hit_rate = _rate(hit_count, evaluable)
    return {
        "strategy_name": strategy_name,
        "evaluable_count": int(evaluable),
        "hit_count": hit_count,
        "miss_count": int(evaluable - hit_count),
        "hit_rate": hit_rate,
        "delta_vs_baseline": round(hit_rate - baseline_rate, 4),
        "draw_prediction_count": int(len(draw_predictions)),
        "draw_hit_count": draw_hit_count,
        "draw_false_count": int(len(draw_predictions) - draw_hit_count),
        "draw_precision": _rate(draw_hit_count, len(draw_predictions)),
        "draw_recall": _rate(draw_hit_count, actual_draw_count),
        "home_hit_rate": _rate(int(home_rows["shadow_hit"].sum()) if not home_rows.empty else 0, len(home_rows)),
        "away_hit_rate": _rate(int(away_rows["shadow_hit"].sum()) if not away_rows.empty else 0, len(away_rows)),
        "actual_draw_count": actual_draw_count,
        "missed_draw_count": int(actual_draw_count - draw_hit_count),
        "newly_captured_draw_count": int(group["newly_captured_draw"].sum()) if not group.empty else 0,
        "newly_created_false_draw_count": int(group["newly_created_false_draw"].sum()) if not group.empty else 0,
    }


def choose_best_strategy(summary: pd.DataFrame) -> dict[str, object]:
    if summary.empty:
        return {}
    ranked = summary.sort_values(["hit_rate", "draw_recall", "draw_false_count", "evaluable_count"], ascending=[False, False, True, False])
    return ranked.iloc[0].to_dict()


def compute_probe_summary(rows: pd.DataFrame, strategy_summary: pd.DataFrame, *, output_dir: Path) -> dict[str, object]:
    baseline = strategy_summary[strategy_summary["strategy_name"].eq("BASELINE")] if not strategy_summary.empty else pd.DataFrame()
    baseline_hit_rate = float(baseline.iloc[0]["hit_rate"]) if not baseline.empty else 0.0
    best = choose_best_strategy(strategy_summary)
    delta = float(best.get("delta_vs_baseline", 0.0)) if best else 0.0
    precision = float(best.get("draw_precision", 0.0)) if best else 0.0
    if delta >= 0.01 and precision >= 0.30:
        recommendation = "DRAW_SHADOW_PROMISING"
    elif delta > 0 and precision < 0.30:
        recommendation = "DRAW_SHADOW_LOW_PRECISION"
    elif delta <= 0:
        recommendation = "DRAW_SHADOW_NOT_HELPFUL"
    else:
        recommendation = "KEEP_AS_DIAGNOSTIC_ONLY"
    return {
        "v2119_draw_signal_shadow_probe_status": "READY",
        "rows_loaded": int(len(rows)),
        "evaluable_count": int(len(rows)),
        "baseline_hit_rate": baseline_hit_rate,
        "best_strategy_name": best.get("strategy_name", "") if best else "",
        "best_strategy_hit_rate": float(best.get("hit_rate", 0.0)) if best else 0.0,
        "best_strategy_delta_vs_baseline": delta,
        "best_strategy_draw_prediction_count": int(best.get("draw_prediction_count", 0)) if best else 0,
        "best_strategy_draw_precision": precision,
        "best_strategy_draw_recall": float(best.get("draw_recall", 0.0)) if best else 0.0,
        "best_strategy_newly_captured_draw_count": int(best.get("newly_captured_draw_count", 0)) if best else 0,
        "best_strategy_newly_created_false_draw_count": int(best.get("newly_created_false_draw_count", 0)) if best else 0,
        "recommendation": recommendation,
        "output_dir": str(output_dir),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }


def render_report(summary: dict[str, object], strategy_summary: pd.DataFrame) -> str:
    return "\n".join([
        "# v2.11.9 Draw Signal Shadow Probe",
        "",
        "Diagnostic-only shadow rules. Final probabilities are not changed.",
        "",
        f"- rows_loaded: {summary['rows_loaded']}",
        f"- baseline_hit_rate: {summary['baseline_hit_rate']}",
        f"- best_strategy_name: {summary['best_strategy_name']}",
        f"- best_strategy_hit_rate: {summary['best_strategy_hit_rate']}",
        f"- best_strategy_delta_vs_baseline: {summary['best_strategy_delta_vs_baseline']}",
        f"- recommendation: {summary['recommendation']}",
        "",
        _markdown_table(strategy_summary),
        "",
        "Safety: automatic_betting_enabled=false, staking_logic_enabled=false, roi_logic_enabled=false.",
    ])


def _baseline_hit_rate(strategy_rows: pd.DataFrame) -> float:
    if strategy_rows.empty:
        return 0.0
    baseline = strategy_rows[strategy_rows["strategy_name"].eq("BASELINE")]
    if baseline.empty:
        return 0.0
    return _rate(int(baseline["shadow_hit"].sum()), len(baseline))


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
