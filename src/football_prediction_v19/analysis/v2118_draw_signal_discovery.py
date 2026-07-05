# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

SIGNAL_COLUMNS = [
    "probability_edge_signal",
    "home_away_probability_similarity",
    "draw_probability_band",
    "team_strength_similarity",
    "goal_profile_balance",
    "low_total_goal_profile",
    "historical_draw_tendency",
]


def analyze_draw_signal_discovery(
    rows: pd.DataFrame,
    *,
    output_dir: str | Path = "outputs/v2118_draw_signal_discovery",
    min_sample: int = 20,
) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    prepared = prepare_signal_rows(rows)
    groups = compute_all_signal_groups(prepared, min_sample=min_sample)
    combos = compute_combo_groups(prepared, min_sample=min_sample)
    summary = compute_discovery_summary(prepared, groups, combos, output_dir=out, min_sample=min_sample)
    groups.to_csv(out / "v2118_draw_signal_groups.csv", index=False)
    combos.to_csv(out / "v2118_draw_signal_combo_groups.csv", index=False)
    top_signal_groups(groups).to_csv(out / "v2118_draw_signal_top_groups.csv", index=False)
    prepared.to_csv(out / "v2118_draw_signal_rows.csv", index=False)
    (out / "v2118_draw_signal_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    (out / "v2118_draw_signal_report.md").write_text(render_report(summary, groups, combos), encoding="utf-8")
    return {
        **summary,
        "signal_groups_csv_path": str((out / "v2118_draw_signal_groups.csv").resolve()),
        "combo_groups_csv_path": str((out / "v2118_draw_signal_combo_groups.csv").resolve()),
        "summary_json_path": str((out / "v2118_draw_signal_summary.json").resolve()),
        "report_md_path": str((out / "v2118_draw_signal_report.md").resolve()),
    }


def prepare_signal_rows(rows: pd.DataFrame) -> pd.DataFrame:
    frame = rows.copy()
    out = pd.DataFrame(index=frame.index)
    for target, candidates in {
        "match_date": ["match_date", "Date"],
        "home_team": ["home_team", "HomeTeam"],
        "away_team": ["away_team", "AwayTeam"],
        "actual_result": ["actual_result", "actual_result_outcome"],
        "home_win_probability": ["home_win_probability", "home_probability"],
        "draw_probability": ["draw_probability"],
        "away_win_probability": ["away_win_probability", "away_probability"],
        "probability_edge": ["probability_edge"],
        "probability_edge_band": ["probability_edge_band"],
    }.items():
        source = next((col for col in candidates if col in frame.columns), None)
        out[target] = frame[source] if source else ""
    for col in ["home_win_probability", "draw_probability", "away_win_probability", "probability_edge"]:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)
    out["actual_result"] = out["actual_result"].astype(str).str.upper()
    out["is_draw"] = out["actual_result"].eq("DRAW")
    out["probability_edge_signal"] = out.apply(probability_edge_signal, axis=1)
    out["home_away_probability_similarity"] = out.apply(home_away_probability_similarity, axis=1)
    out["draw_probability_band"] = out["draw_probability"].map(draw_probability_band)
    out["team_strength_similarity"] = _optional_bucket(frame, ["team_strength_similarity", "strength_similarity_band", "ppg_gap_band", "gd_gap_band"], "UNKNOWN")
    out["goal_profile_balance"] = _optional_bucket(frame, ["goal_profile_balance", "goal_balance_band", "gf_ga_balance_band"], "UNKNOWN")
    out["low_total_goal_profile"] = _optional_bucket(frame, ["low_total_goal_profile", "total_goal_profile_band", "expected_total_goal_band"], "UNKNOWN")
    out["historical_draw_tendency"] = _optional_bucket(frame, ["historical_draw_tendency", "draw_tendency_band", "h2h_draw_tendency_band"], "UNKNOWN")
    return out[out["actual_result"].isin(["HOME", "DRAW", "AWAY"])].copy()


def probability_edge_signal(row: pd.Series) -> str:
    edge = float(row.get("probability_edge", 0.0))
    if edge <= 0.03:
        return "EDGE_0_3"
    if edge <= 0.06:
        return "EDGE_3_6"
    if edge <= 0.10:
        return "EDGE_6_10"
    return "EDGE_10_PLUS"


def home_away_probability_similarity(row: pd.Series) -> str:
    gap = abs(float(row.get("home_win_probability", 0.0)) - float(row.get("away_win_probability", 0.0)))
    if gap <= 0.03:
        return "HA_SIMILAR_0_3"
    if gap <= 0.06:
        return "HA_SIMILAR_3_6"
    if gap <= 0.10:
        return "HA_SIMILAR_6_10"
    return "HA_GAP_10_PLUS"


def draw_probability_band(value: object) -> str:
    draw = float(value or 0.0)
    if draw < 0.26:
        return "DRAW_LT_26"
    if draw < 0.28:
        return "DRAW_26_28"
    if draw < 0.30:
        return "DRAW_28_30"
    if draw < 0.32:
        return "DRAW_30_32"
    return "DRAW_32_PLUS"


def compute_all_signal_groups(rows: pd.DataFrame, *, min_sample: int = 20) -> pd.DataFrame:
    baseline = baseline_draw_rate(rows)
    records = []
    for signal in SIGNAL_COLUMNS:
        if signal not in rows.columns:
            continue
        for group, subset in rows.groupby(signal, dropna=False):
            records.append(_group_record(signal, str(group), subset, baseline, min_sample))
    return pd.DataFrame(records)


def compute_combo_groups(rows: pd.DataFrame, *, min_sample: int = 20) -> pd.DataFrame:
    baseline = baseline_draw_rate(rows)
    combos = [
        ("EDGE_X_HA_SIMILARITY", ["probability_edge_signal", "home_away_probability_similarity"]),
        ("EDGE_X_DRAW_BAND", ["probability_edge_signal", "draw_probability_band"]),
        ("HA_SIMILARITY_X_DRAW_BAND", ["home_away_probability_similarity", "draw_probability_band"]),
        ("LOW_GOAL_X_DRAW_BAND", ["low_total_goal_profile", "draw_probability_band"]),
        ("STRENGTH_X_HA_SIMILARITY", ["team_strength_similarity", "home_away_probability_similarity"]),
    ]
    records = []
    for name, cols in combos:
        if any(col not in rows.columns for col in cols):
            continue
        for values, subset in rows.groupby(cols, dropna=False):
            if not isinstance(values, tuple):
                values = (values,)
            records.append(_group_record(name, " | ".join(str(v) for v in values), subset, baseline, min_sample))
    return pd.DataFrame(records)


def top_signal_groups(groups: pd.DataFrame, *, min_sample: int = 20) -> pd.DataFrame:
    if groups.empty:
        return groups.copy()
    ranked = groups.copy()
    ranked["sample_rank"] = ranked["count"].ge(min_sample).astype(int)
    return ranked.sort_values(["sample_rank", "draw_rate", "count"], ascending=[False, False, False]).drop(columns=["sample_rank"]).reset_index(drop=True)


def compute_discovery_summary(rows: pd.DataFrame, groups: pd.DataFrame, combos: pd.DataFrame, *, output_dir: Path, min_sample: int = 20) -> dict[str, object]:
    baseline = baseline_draw_rate(rows)
    best_signal = _best_group(groups, min_sample=min_sample)
    best_combo = _best_group(combos, min_sample=min_sample)
    signal_found = bool(best_signal and float(best_signal.get("lift_vs_baseline", 0.0)) >= 0.05 and int(best_signal.get("count", 0)) >= min_sample)
    combo_found = bool(best_combo and float(best_combo.get("lift_vs_baseline", 0.0)) >= 0.05 and int(best_combo.get("count", 0)) >= min_sample)
    recommendation = "DRAW_SIGNAL_PROMISING" if signal_found or combo_found else "KEEP_AS_DIAGNOSTIC_ONLY"
    return {
        "v2118_draw_signal_discovery_status": "READY",
        "rows_loaded": int(len(rows)),
        "evaluable_count": int(len(rows)),
        "baseline_draw_rate": baseline,
        "actual_draw_count": int(rows["is_draw"].sum()) if not rows.empty else 0,
        "best_signal_name": best_signal.get("signal_name", "") if best_signal else "",
        "best_signal_group": best_signal.get("signal_group", "") if best_signal else "",
        "best_signal_count": int(best_signal.get("count", 0)) if best_signal else 0,
        "best_signal_draw_rate": float(best_signal.get("draw_rate", 0.0)) if best_signal else 0.0,
        "best_signal_lift_vs_baseline": float(best_signal.get("lift_vs_baseline", 0.0)) if best_signal else 0.0,
        "best_combo_name": best_combo.get("signal_name", "") if best_combo else "",
        "best_combo_count": int(best_combo.get("count", 0)) if best_combo else 0,
        "best_combo_draw_rate": float(best_combo.get("draw_rate", 0.0)) if best_combo else 0.0,
        "best_combo_lift_vs_baseline": float(best_combo.get("lift_vs_baseline", 0.0)) if best_combo else 0.0,
        "draw_signal_found": bool(signal_found or combo_found),
        "recommendation": recommendation,
        "output_dir": str(output_dir),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }


def render_report(summary: dict[str, object], groups: pd.DataFrame, combos: pd.DataFrame) -> str:
    return "\n".join([
        "# v2.11.8 Draw Signal Discovery",
        "",
        "Diagnostic-only discovery. No final probabilities are changed.",
        "",
        f"- rows_loaded: {summary['rows_loaded']}",
        f"- baseline_draw_rate: {summary['baseline_draw_rate']}",
        f"- best_signal_name: {summary['best_signal_name']}",
        f"- best_signal_group: {summary['best_signal_group']}",
        f"- best_signal_draw_rate: {summary['best_signal_draw_rate']}",
        f"- best_combo_name: {summary['best_combo_name']}",
        f"- best_combo_draw_rate: {summary['best_combo_draw_rate']}",
        f"- recommendation: {summary['recommendation']}",
        "",
        "## Top Signal Groups",
        _markdown_table(top_signal_groups(groups).head(10)),
        "",
        "## Top Combo Groups",
        _markdown_table(top_signal_groups(combos).head(10)),
        "",
        "Safety: automatic_betting_enabled=false, staking_logic_enabled=false, roi_logic_enabled=false.",
    ])


def baseline_draw_rate(rows: pd.DataFrame) -> float:
    return _rate(int(rows["is_draw"].sum()) if not rows.empty and "is_draw" in rows.columns else 0, len(rows))


def _group_record(signal_name: str, signal_group: str, subset: pd.DataFrame, baseline: float, min_sample: int) -> dict[str, object]:
    draw_count = int(subset["is_draw"].sum()) if not subset.empty else 0
    draw_rate = _rate(draw_count, len(subset))
    return {
        "signal_name": signal_name,
        "signal_group": signal_group,
        "count": int(len(subset)),
        "draw_count": draw_count,
        "draw_rate": draw_rate,
        "lift_vs_baseline": round(draw_rate - baseline, 4),
        "low_sample": bool(len(subset) < min_sample),
    }


def _best_group(groups: pd.DataFrame, *, min_sample: int = 20) -> dict[str, object]:
    if groups.empty:
        return {}
    preferred = groups[groups["count"].ge(min_sample)]
    pool = preferred if not preferred.empty else groups
    ranked = pool.sort_values(["draw_rate", "count"], ascending=[False, False])
    return ranked.iloc[0].to_dict()


def _optional_bucket(frame: pd.DataFrame, candidates: list[str], default: str) -> pd.Series:
    source = next((col for col in candidates if col in frame.columns), None)
    if source:
        return frame[source].astype(str).replace("", default)
    return pd.Series(default, index=frame.index)


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
