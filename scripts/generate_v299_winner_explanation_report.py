# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

PROMISING = {
    "GOAL_DIFFERENCE": ("gd_adjusted_home_win_probability", "gd_adjusted_away_probability", "gd_adjustment_applied"),
    "GOALS_FOR": ("gf_adjusted_home_win_probability", "gf_adjusted_away_probability", "gf_adjustment_applied"),
    "GOALS_AGAINST": ("ga_adjusted_home_win_probability", "ga_adjusted_away_probability", "ga_adjustment_applied"),
}


def generate_winner_explanation_report(rows: str | Path, output_dir: str | Path = "outputs/v299_winner_explanation_report") -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(rows, keep_default_na=False)
    work = build_explanation_frame(frame)
    summary = build_explanation_summary(work)
    rows_path = out / "v299_winner_explanation_rows.csv"
    json_path = out / "v299_winner_explanation_summary.json"
    md_path = out / "v299_winner_explanation_report.md"
    work.to_csv(rows_path, index=False)
    json_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    md_path.write_text(_markdown(work, summary), encoding="utf-8")
    return {**summary, "rows_csv_path": str(rows_path.resolve()), "summary_json_path": str(json_path.resolve()), "report_md_path": str(md_path.resolve())}


def build_explanation_frame(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    _ensure_probability_columns(work)
    work["base_probability_edge"] = (work["base_home_win_probability"] - work["base_away_probability"]).round(4)
    work["base_direction"] = [direction_from_edge(edge) for edge in work["base_probability_edge"]]
    for prefix, (home_col, away_col, _) in PROMISING.items():
        column = _prefix_to_column(prefix)
        work[f"{column}_shadow_direction"] = [direction_from_edge(_num(home) - _num(away)) for home, away in zip(work[home_col], work[away_col], strict=False)]
    support_counts = []
    conflict_counts = []
    consensus_values = []
    strongest_values = []
    labels = []
    texts = []
    for _, row in work.iterrows():
        support = promising_indicator_support_count(row)
        conflict = promising_indicator_conflict_count(row)
        consensus = promising_indicator_consensus(row)
        strongest = strongest_shadow_indicator(row)
        label = explanation_label(row, support, conflict, consensus)
        support_counts.append(support)
        conflict_counts.append(conflict)
        consensus_values.append(consensus)
        strongest_values.append(strongest)
        labels.append(label)
        texts.append(explanation_text(row, label, consensus))
    work["promising_indicator_support_count"] = support_counts
    work["promising_indicator_conflict_count"] = conflict_counts
    work["promising_indicator_consensus"] = consensus_values
    work["strongest_shadow_indicator"] = strongest_values
    work["explanation_label"] = labels
    work["explanation_text"] = texts
    return work


def direction_from_edge(edge: object) -> str:
    value = round(_num(edge), 4)
    if value >= 0.04:
        return "HOME"
    if value <= -0.04:
        return "AWAY"
    return "NO_CLEAR_WINNER"


def promising_indicator_support_count(row: pd.Series) -> int:
    base = str(row.get("base_direction", "NO_CLEAR_WINNER"))
    if base == "NO_CLEAR_WINNER":
        return 0
    return sum(1 for direction in _promising_directions(row) if direction == base)


def promising_indicator_conflict_count(row: pd.Series) -> int:
    base = str(row.get("base_direction", "NO_CLEAR_WINNER"))
    if base == "NO_CLEAR_WINNER":
        return 0
    opposite = "AWAY" if base == "HOME" else "HOME"
    return sum(1 for direction in _promising_directions(row) if direction == opposite)


def promising_indicator_consensus(row: pd.Series) -> str:
    directions = [direction for direction in _promising_directions(row) if direction in {"HOME", "AWAY"}]
    if not directions:
        return "NO_CLEAR_WINNER"
    home = directions.count("HOME")
    away = directions.count("AWAY")
    if home > away:
        return "HOME"
    if away > home:
        return "AWAY"
    return "MIXED"


def strongest_shadow_indicator(row: pd.Series) -> str:
    shifts = {
        "GOAL_DIFFERENCE": abs(_num(row.get("gd_adjusted_home_win_probability", 0)) - _num(row.get("base_home_win_probability", 0))) + abs(_num(row.get("gd_adjusted_away_probability", 0)) - _num(row.get("base_away_probability", 0))),
        "GOALS_FOR": abs(_num(row.get("gf_adjusted_home_win_probability", 0)) - _num(row.get("base_home_win_probability", 0))) + abs(_num(row.get("gf_adjusted_away_probability", 0)) - _num(row.get("base_away_probability", 0))),
        "GOALS_AGAINST": abs(_num(row.get("ga_adjusted_home_win_probability", 0)) - _num(row.get("base_home_win_probability", 0))) + abs(_num(row.get("ga_adjusted_away_probability", 0)) - _num(row.get("base_away_probability", 0))),
    }
    name, value = max(shifts.items(), key=lambda item: item[1])
    return name if value > 0 else "NONE"


def explanation_label(row: pd.Series, support_count: int | None = None, conflict_count: int | None = None, consensus: str | None = None) -> str:
    if str(row.get("winner_analysis_status", "")) == "DATA_BLOCKED" or str(row.get("decision_class", "")) == "DATA_BLOCKED":
        return "DATA_BLOCKED_OR_UNKNOWN"
    support = promising_indicator_support_count(row) if support_count is None else support_count
    conflict = promising_indicator_conflict_count(row) if conflict_count is None else conflict_count
    vote = promising_indicator_consensus(row) if consensus is None else consensus
    base = str(row.get("base_direction", "NO_CLEAR_WINNER"))
    if base == "NO_CLEAR_WINNER":
        if vote == "HOME":
            return "NO_DECISION_SHADOW_HOME"
        if vote == "AWAY":
            return "NO_DECISION_SHADOW_AWAY"
        return "NO_DECISION_NO_SIGNAL"
    edge = abs(_num(row.get("base_probability_edge", 0.0)))
    if support >= 2 and conflict == 0:
        return "BASE_AND_SHADOWS_ALIGN"
    if conflict >= 2 and edge >= 0.08:
        return "BASE_STRONG_SHADOW_CONFLICT"
    if support >= conflict:
        return "BASE_WEAK_SHADOW_SUPPORT"
    return "BASE_WEAK_SHADOW_CONFLICT"


def explanation_text(row: pd.Series, label: str, consensus: str) -> str:
    base = str(row.get("base_direction", "NO_CLEAR_WINNER"))
    if label == "BASE_AND_SHADOWS_ALIGN":
        return f"Base leans {base} and GD/GF/GA mostly support {base}."
    if label in {"BASE_STRONG_SHADOW_CONFLICT", "BASE_WEAK_SHADOW_CONFLICT"}:
        return f"Base leans {base} but promising shadows point to {consensus} or are mixed."
    if label == "BASE_WEAK_SHADOW_SUPPORT":
        return f"Base leans {base} with partial support from promising shadows."
    if label == "NO_DECISION_SHADOW_HOME":
        return "Base is unclear but promising shadows lean HOME."
    if label == "NO_DECISION_SHADOW_AWAY":
        return "Base is unclear but promising shadows lean AWAY."
    if label == "NO_DECISION_NO_SIGNAL":
        return "No clear base edge and no useful shadow support."
    return "Data blocked or missing required probabilities."


def build_explanation_summary(work: pd.DataFrame) -> dict[str, object]:
    decisions = work["evaluation_result"].astype(str).isin(["HIT", "MISS"]) if "evaluation_result" in work else pd.Series([False] * len(work))
    hits = work["evaluation_result"].astype(str).eq("HIT") if "evaluation_result" in work else pd.Series([False] * len(work))
    label_counts = work["explanation_label"].value_counts().to_dict() if "explanation_label" in work else {}
    strongest_counts = work["strongest_shadow_indicator"].value_counts().to_dict() if "strongest_shadow_indicator" in work else {}
    support_rows = work["promising_indicator_support_count"].astype(int) > 0 if "promising_indicator_support_count" in work else pd.Series([False] * len(work))
    conflict_rows = work["promising_indicator_conflict_count"].astype(int) > 0 if "promising_indicator_conflict_count" in work else pd.Series([False] * len(work))
    return {
        "v299_winner_explanation_report_status": "READY",
        "rows_analyzed": int(len(work)),
        "decision_count": int(decisions.sum()),
        "no_decision_count": int(work.get("decision_class", pd.Series([], dtype=str)).astype(str).eq("NO_DECISION").sum()) if "decision_class" in work else 0,
        "data_blocked_count": int(work.get("decision_class", pd.Series([], dtype=str)).astype(str).eq("DATA_BLOCKED").sum()) if "decision_class" in work else 0,
        "base_hit_rate": _rate(int(hits.sum()), int(decisions.sum())),
        "base_direction_home_count": int(work["base_direction"].astype(str).eq("HOME").sum()),
        "base_direction_away_count": int(work["base_direction"].astype(str).eq("AWAY").sum()),
        "base_direction_unclear_count": int(work["base_direction"].astype(str).eq("NO_CLEAR_WINNER").sum()),
        "promising_indicator_consensus_home_count": int(work["promising_indicator_consensus"].astype(str).eq("HOME").sum()),
        "promising_indicator_consensus_away_count": int(work["promising_indicator_consensus"].astype(str).eq("AWAY").sum()),
        "promising_indicator_consensus_mixed_count": int(work["promising_indicator_consensus"].astype(str).isin(["MIXED", "NO_CLEAR_WINNER"]).sum()),
        "promising_indicator_consensus_count": int(work["promising_indicator_consensus"].astype(str).isin(["HOME", "AWAY"]).sum()),
        "promising_indicator_conflict_count": int(conflict_rows.sum()),
        "shadow_supports_base_count": int(support_rows.sum()),
        "shadow_contradicts_base_count": int(conflict_rows.sum()),
        "explanation_label_counts": label_counts,
        "strongest_shadow_indicator_counts": strongest_counts,
        "strongest_shadow_indicator": max(strongest_counts, key=strongest_counts.get) if strongest_counts else "NONE",
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }


def _ensure_probability_columns(work: pd.DataFrame) -> None:
    defaults = {
        "base_home_win_probability": "home_win_probability",
        "base_draw_probability": "draw_probability",
        "base_away_probability": "away_win_probability",
        "gd_adjusted_home_win_probability": "base_home_win_probability",
        "gd_adjusted_away_probability": "base_away_probability",
        "gf_adjusted_home_win_probability": "base_home_win_probability",
        "gf_adjusted_away_probability": "base_away_probability",
        "ga_adjusted_home_win_probability": "base_home_win_probability",
        "ga_adjusted_away_probability": "base_away_probability",
    }
    for column, fallback in defaults.items():
        if column not in work.columns:
            work[column] = work.get(fallback, 0.0)
    for column in defaults:
        work[column] = pd.to_numeric(work[column], errors="coerce").fillna(0.0)
    for column in ["home_win_probability", "draw_probability", "away_win_probability"]:
        if column not in work.columns:
            work[column] = 0.0


def _promising_directions(row: pd.Series) -> list[str]:
    return [
        str(row.get("gd_shadow_direction", "NO_CLEAR_WINNER")),
        str(row.get("gf_shadow_direction", "NO_CLEAR_WINNER")),
        str(row.get("ga_shadow_direction", "NO_CLEAR_WINNER")),
    ]


def _prefix_to_column(prefix: str) -> str:
    return {"GOAL_DIFFERENCE": "gd", "GOALS_FOR": "gf", "GOALS_AGAINST": "ga"}[prefix]


def _rate(numerator: int, denominator: int) -> float:
    return round(float(numerator / denominator), 4) if denominator else 0.0


def _num(value: object) -> float:
    try:
        if str(value).strip() == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _markdown(work: pd.DataFrame, summary: dict[str, object]) -> str:
    return "\n".join(
        [
            "# v2.9.9 Winner Explanation Report",
            "",
            "## Safety",
            "- automatic_betting_enabled: false",
            "- staking_logic_enabled: false",
            "- roi_logic_enabled: false",
            "- No productive betting logic",
            "",
            "## Executive Summary",
            f"- rows_analyzed: {summary['rows_analyzed']}",
            f"- decision_count: {summary['decision_count']}",
            f"- no_decision_count: {summary['no_decision_count']}",
            f"- base_hit_rate: {summary['base_hit_rate']}",
            f"- shadow_supports_base_count: {summary['shadow_supports_base_count']}",
            f"- shadow_contradicts_base_count: {summary['shadow_contradicts_base_count']}",
            f"- strongest_shadow_indicator: {summary['strongest_shadow_indicator']}",
            "",
            "## Explanation Label Counts",
            _table_from_counts(summary["explanation_label_counts"], "explanation_label"),
            "",
            "## Strongest Shadow Indicator Counts",
            _table_from_counts(summary["strongest_shadow_indicator_counts"], "strongest_shadow_indicator"),
            "",
            "## Best Explained Hits",
            _rows_table(work[(work["explanation_label"].eq("BASE_AND_SHADOWS_ALIGN")) & (work.get("evaluation_result", "").astype(str).eq("HIT"))].head(10)),
            "",
            "## Most Important Misses",
            _rows_table(work[work.get("evaluation_result", "").astype(str).eq("MISS")].head(10)),
            "",
            "## No Decision With Shadow Signal",
            _rows_table(work[(work.get("decision_class", "").astype(str).eq("NO_DECISION")) & (work["promising_indicator_consensus"].isin(["HOME", "AWAY"]))].head(10)),
            "",
            "## Conclusion",
            "Keine finale Probability-Aenderung. Kein produktiver Mix. Report dient nur zur Diagnose. Naechster Schritt soll erst nach Lesen des Reports entschieden werden.",
            "",
        ]
    )


def _table_from_counts(counts: dict[str, int], label: str) -> str:
    lines = [f"| {label} | count |", "|---|---:|"]
    for key, value in counts.items():
        lines.append(f"| {key} | {value} |")
    return "\n".join(lines)


def _rows_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    cols = [col for col in ["competition", "home_team", "away_team", "input_match_date", "real_result", "evaluation_result", "base_direction", "promising_indicator_consensus", "strongest_shadow_indicator", "explanation_label"] if col in frame.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, row in frame[cols].iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in cols) + " |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", default="outputs/v27_prematch_evaluation/v27_prematch_evaluation_rows.csv")
    parser.add_argument("--output-dir", default="outputs/v299_winner_explanation_report")
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)
    result = generate_winner_explanation_report(args.rows, args.output_dir)
    for key in [
        "v299_winner_explanation_report_status",
        "rows_analyzed",
        "decision_count",
        "no_decision_count",
        "base_hit_rate",
        "promising_indicator_consensus_count",
        "promising_indicator_conflict_count",
        "shadow_supports_base_count",
        "shadow_contradicts_base_count",
        "strongest_shadow_indicator",
        "automatic_betting_enabled",
        "staking_logic_enabled",
        "roi_logic_enabled",
    ]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
