# -*- coding: utf-8 -*-
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any

import pandas as pd


def analyze_v27_coverage(rows_csv: str | Path) -> dict[str, object]:
    rows = pd.read_csv(rows_csv, keep_default_na=False)
    requested = int(len(rows))
    ready = _ready_mask(rows)
    blocked = rows.get("evaluation_result", pd.Series([""] * requested)).astype(str).eq("DATA_BLOCKED")
    not_found = rows.get("fixture_resolver_status", pd.Series([""] * requested)).astype(str).eq("NOT_FOUND")
    zero_probs = _zero_probability_mask(rows)
    summary = {
        "matches_requested": requested,
        "ready_count": int(ready.sum()),
        "ready_rate": _rate(int(ready.sum()), requested),
        "data_blocked_count": int(blocked.sum()),
        "data_blocked_rate": _rate(int(blocked.sum()), requested),
        "not_found_count": int(not_found.sum()),
        "not_found_rate": _rate(int(not_found.sum()), requested),
        "result_known_count": int(rows.get("result_status", pd.Series([""] * requested)).astype(str).eq("RESOLVED").sum()),
        "zero_probability_count": int(zero_probs.sum()),
        "ready_with_probabilities_count": int((ready & ~zero_probs).sum()),
        "blocked_by_competition": _counts_by(rows[blocked], "competition"),
        "ready_by_competition": _counts_by(rows[ready], "competition"),
        "top_block_reasons": _top_block_reasons(rows),
        "recommendation": "",
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }
    summary["recommendation"] = _recommendation(summary)
    return summary


def write_v28_coverage_report(rows_csv: str | Path, output_dir: str | Path = "outputs/v28_coverage") -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary = {"v28_coverage_status": "READY", **analyze_v27_coverage(rows_csv)}
    json_path = out / "coverage_summary.json"
    md_path = out / "coverage_report.md"
    json_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    md_path.write_text(_markdown(summary), encoding="utf-8")
    return {**summary, "coverage_summary_json_path": str(json_path.resolve()), "coverage_report_md_path": str(md_path.resolve())}


def _ready_mask(rows: pd.DataFrame) -> pd.Series:
    if rows.empty:
        return pd.Series(dtype=bool)
    winner_ready = rows.get("winner_analysis_status", pd.Series([""] * len(rows))).astype(str).eq("READY")
    asof_clean = rows.get("asof_guard_status", pd.Series([""] * len(rows))).astype(str).isin(["CLEAN", "WARNING"])
    return winner_ready & asof_clean & ~_zero_probability_mask(rows)


def _zero_probability_mask(rows: pd.DataFrame) -> pd.Series:
    home = pd.to_numeric(rows.get("home_win_probability", pd.Series([0] * len(rows))), errors="coerce").fillna(0)
    draw = pd.to_numeric(rows.get("draw_probability", pd.Series([0] * len(rows))), errors="coerce").fillna(0)
    away = pd.to_numeric(rows.get("away_win_probability", pd.Series([0] * len(rows))), errors="coerce").fillna(0)
    return home.eq(0) & draw.eq(0) & away.eq(0)


def _counts_by(rows: pd.DataFrame, column: str) -> dict[str, int]:
    if rows.empty or column not in rows:
        return {}
    return {str(key): int(value) for key, value in rows[column].astype(str).value_counts().items()}


def _top_block_reasons(rows: pd.DataFrame) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for column in ["resolver_reason", "block_reason_text", "risk_notes"]:
        if column not in rows:
            continue
        for value in rows[column].fillna("").astype(str):
            text = value.strip()
            if text:
                counter[text] += 1
    return dict(counter.most_common(10))


def _recommendation(summary: dict[str, Any]) -> str:
    if float(summary.get("data_blocked_rate", 0.0)) > 0.5:
        if int(summary.get("not_found_count", 0)) >= max(1, int(summary.get("data_blocked_count", 0)) // 2):
            return "USE_FIXTURE_SOURCE_SUPPORTED_SAMPLE_OR_ADD_LEAGUE_SOURCE_MAPPING"
        return "BUILD_SOURCE_SUPPORTED_SAMPLE"
    return "KEEP_CURRENT_SAMPLE"


def _rate(numerator: int, denominator: int) -> float:
    return round(float(numerator / denominator), 4) if denominator else 0.0


def _markdown(summary: dict[str, object]) -> str:
    return "\n".join(
        [
            "# v2.8 Coverage Diagnostics",
            "",
            f"- v28_coverage_status: {summary['v28_coverage_status']}",
            f"- matches_requested: {summary['matches_requested']}",
            f"- ready_count: {summary['ready_count']}",
            f"- ready_rate: {summary['ready_rate']}",
            f"- data_blocked_count: {summary['data_blocked_count']}",
            f"- data_blocked_rate: {summary['data_blocked_rate']}",
            f"- not_found_count: {summary['not_found_count']}",
            f"- recommendation: {summary['recommendation']}",
            "",
            "## Safety",
            "- automatic_betting_enabled: false",
            "- staking_logic_enabled: false",
            "- roi_logic_enabled: false",
            "",
            "No betting metrics, no stake, no ROI, no profit, no yield, no bankroll logic.",
            "",
        ]
    )
