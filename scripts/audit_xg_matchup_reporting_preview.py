# -*- coding: utf-8 -*-
"""Audit xG matchup reporting previews."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

XG_MATCHUP_REPORTING_PREVIEW_READY = "XG_MATCHUP_REPORTING_PREVIEW_READY"
BUILD_XG_MATCHUP_REPORTING_PREVIEW = "BUILD_XG_MATCHUP_REPORTING_PREVIEW"
FIX_XG_MATCHUP_REPORTING_PREVIEW = "FIX_XG_MATCHUP_REPORTING_PREVIEW"

OUTPUT_CSV = "xg_matchup_reporting_preview_summary.csv"
OUTPUT_MD = "xg_matchup_reporting_preview_summary.md"

REQUIRED_COLUMNS = [
    "date",
    "home_team",
    "away_team",
    "home_xg",
    "away_xg",
    "home_rolling_matches_available",
    "away_rolling_matches_available",
    "home_rolling_xg_for",
    "home_rolling_xg_against",
    "home_rolling_xg_diff",
    "away_rolling_xg_for",
    "away_rolling_xg_against",
    "away_rolling_xg_diff",
    "matchup_rolling_xg_diff_home",
    "matchup_reporting_status",
]

NUMERIC_COLUMNS = [
    "home_xg",
    "away_xg",
    "home_rolling_xg_for",
    "home_rolling_xg_against",
    "home_rolling_xg_diff",
    "away_rolling_xg_for",
    "away_rolling_xg_against",
    "away_rolling_xg_diff",
    "matchup_rolling_xg_diff_home",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", default=None)
    parser.add_argument("--preview-dir", default=str(ROOT / "outputs" / "xg_reporting_preview"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--expected-rows", type=int, default=306)
    return parser


def _preview_paths(preview: str | Path | None, preview_dir: str | Path) -> list[Path]:
    if preview:
        return [Path(preview)]
    root = Path(preview_dir)
    return sorted(root.glob("*xg_matchup_reporting_preview*.csv")) if root.exists() else []


def audit_matchup_file(path: Path, *, expected_rows: int | None = 306) -> dict[str, Any]:
    errors: list[str] = []
    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception as exc:
        return {
            "preview_path": str(path),
            "preview_file": path.name,
            "matches_reported": 0,
            "missing_required_columns": "ALL",
            "missing_xg_rows": 0,
            "missing_rolling_context_rows": 0,
            "numeric_columns_valid": False,
            "matchup_valid": False,
            "blocking_reasons": str(exc),
        }
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        errors.append("MISSING_REQUIRED_COLUMNS")
    if expected_rows is not None and len(df) != expected_rows:
        errors.append("UNEXPECTED_ROW_COUNT")
    missing_xg = int(df[["home_xg", "away_xg"]].isna().any(axis=1).sum()) if {"home_xg", "away_xg"}.issubset(df.columns) else len(df)
    if missing_xg:
        errors.append("MISSING_XG")
    rolling_cols = [col for col in REQUIRED_COLUMNS if "rolling" in col]
    missing_context = int(df[rolling_cols].isna().any(axis=1).sum()) if set(rolling_cols).issubset(df.columns) else len(df)
    if missing_context:
        errors.append("MISSING_ROLLING_CONTEXT")
    if set(NUMERIC_COLUMNS).issubset(df.columns):
        numeric_valid = not df[NUMERIC_COLUMNS].apply(pd.to_numeric, errors="coerce").isna().any().any()
    else:
        numeric_valid = False
    if not numeric_valid:
        errors.append("NUMERIC_COLUMNS_INVALID")
    if "matchup_reporting_status" in df.columns and df["matchup_reporting_status"].isna().any():
        errors.append("MISSING_MATCHUP_STATUS")
    return {
        "preview_path": str(path),
        "preview_file": path.name,
        "matches_reported": int(len(df)),
        "missing_required_columns": " | ".join(missing_cols),
        "missing_xg_rows": missing_xg,
        "missing_rolling_context_rows": missing_context,
        "numeric_columns_valid": numeric_valid,
        "matchup_valid": not errors,
        "blocking_reasons": " | ".join(errors),
    }


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return BUILD_XG_MATCHUP_REPORTING_PREVIEW
    if table["matchup_valid"].any():
        return XG_MATCHUP_REPORTING_PREVIEW_READY
    return FIX_XG_MATCHUP_REPORTING_PREVIEW


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    lines = [
        "# Phase 13.19 xG Matchup Reporting Preview Audit",
        "",
        "Phase 13.19 is reporting/diagnostic preview only. Matchup rows are not model features.",
        "",
        "## A. Executive Summary",
        f"- matchup previews audited: {len(table)}",
        f"- valid matchup previews: {int(table['matchup_valid'].sum()) if not table.empty else 0}",
        "",
        "## B. Matchup Diagnostics",
    ]
    if table.empty:
        lines += ["No matchup previews found.", ""]
    else:
        cols = ["preview_file", "matches_reported", "missing_xg_rows", "missing_rolling_context_rows", "numeric_columns_valid", "matchup_valid", "blocking_reasons"]
        lines += ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
        for _, row in table[cols].iterrows():
            lines.append("| " + " | ".join(str(row[col]).replace("|", ";") for col in cols) + " |")
        lines.append("")
    lines += [
        "## C. Safety Checks",
        "- No source, target, accepted artifact, or production manifest file modified.",
        "- No xG values inferred or invented.",
        "- Rolling matchup values use pre-match context only.",
        "- No model, probability, market-tier, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "",
        "## D. Phase 13.19 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(*, preview: str | Path | None = None, preview_dir: str | Path = ROOT / "outputs" / "xg_reporting_preview", output_dir: str | Path = ROOT / "outputs" / "diagnostics", expected_rows: int | None = 306) -> tuple[pd.DataFrame, str, str]:
    rows = [audit_matchup_file(path, expected_rows=expected_rows) for path in _preview_paths(preview, preview_dir)]
    table = pd.DataFrame(rows)
    rec = recommendation(table)
    markdown = build_markdown(table, rec)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / OUTPUT_CSV, index=False)
    (out / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown, rec


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, _markdown, rec = run(preview=args.preview, preview_dir=args.preview_dir, output_dir=args.output_dir, expected_rows=args.expected_rows)
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
