# -*- coding: utf-8 -*-
"""Audit xG reporting preview CSVs."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

XG_REPORTING_PREVIEW_READY = "XG_REPORTING_PREVIEW_READY"
BUILD_XG_REPORTING_PREVIEW = "BUILD_XG_REPORTING_PREVIEW"
FIX_XG_REPORTING_PREVIEW = "FIX_XG_REPORTING_PREVIEW"

OUTPUT_CSV = "xg_reporting_preview_summary.csv"
OUTPUT_MD = "xg_reporting_preview_summary.md"

REQUIRED_REPORTING_COLUMNS = [
    "home_xg",
    "away_xg",
    "xg_total",
    "xg_diff_home",
    "goal_diff_home",
    "home_xg_minus_goals",
    "away_xg_minus_goals",
    "xg_result_label",
    "actual_result_label",
    "xg_result_matches_actual",
    "xg_reporting_status",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", default=None)
    parser.add_argument("--preview-dir", default=str(ROOT / "outputs" / "xg_reporting_preview"))
    parser.add_argument("--target", default=str(ROOT / "data" / "processed" / "football_data_D1_2024_clean.csv"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--expected-rows", type=int, default=306)
    return parser


def _preview_paths(preview: str | Path | None, preview_dir: str | Path) -> list[Path]:
    if preview:
        return [Path(preview)]
    root = Path(preview_dir)
    return sorted(root.glob("*.csv")) if root.exists() else []


def _identity_columns(df: pd.DataFrame) -> list[str]:
    candidates = ["date", "Date", "home_team", "HomeTeam", "away_team", "AwayTeam", "score", "FTHG", "FTAG", "FTR", "home_goals", "away_goals"]
    return [col for col in candidates if col in df.columns]


def audit_preview_file(path: Path, *, target: Path | None, expected_rows: int | None) -> dict[str, Any]:
    errors: list[str] = []
    try:
        preview = pd.read_csv(path, low_memory=False)
    except Exception as exc:
        return {
            "preview_path": str(path),
            "preview_file": path.name,
            "row_count": 0,
            "missing_reporting_columns": "ALL",
            "missing_xg_rows": 0,
            "non_numeric_xg_rows": 0,
            "identity_columns_unchanged": False,
            "preview_valid": False,
            "blocking_reasons": str(exc),
        }
    missing_cols = [col for col in REQUIRED_REPORTING_COLUMNS if col not in preview.columns]
    if missing_cols:
        errors.append("MISSING_REPORTING_COLUMNS")
    if expected_rows is not None and len(preview) != expected_rows:
        errors.append("UNEXPECTED_ROW_COUNT")
    if {"home_xg", "away_xg"}.issubset(preview.columns):
        numeric = preview[["home_xg", "away_xg"]].apply(pd.to_numeric, errors="coerce")
        missing_xg = int(preview[["home_xg", "away_xg"]].isna().any(axis=1).sum())
        non_numeric = int(numeric.isna().any(axis=1).sum() - missing_xg)
        if missing_xg:
            errors.append("MISSING_XG_VALUES")
        if non_numeric:
            errors.append("NON_NUMERIC_XG_VALUES")
    else:
        missing_xg = len(preview)
        non_numeric = 0
    identity_unchanged = False
    if target is not None and target.exists():
        target_df = pd.read_csv(target, low_memory=False)
        cols = _identity_columns(target_df)
        identity_unchanged = bool(cols) and len(target_df) == len(preview) and preview[cols].equals(target_df[cols])
        if not identity_unchanged:
            errors.append("IDENTITY_COLUMNS_CHANGED")
    elif target is None:
        identity_unchanged = True
    else:
        errors.append("TARGET_NOT_FOUND")
    return {
        "preview_path": str(path),
        "preview_file": path.name,
        "row_count": int(len(preview)),
        "missing_reporting_columns": " | ".join(missing_cols),
        "missing_xg_rows": missing_xg,
        "non_numeric_xg_rows": non_numeric,
        "identity_columns_unchanged": identity_unchanged,
        "preview_valid": not errors,
        "blocking_reasons": " | ".join(errors),
    }


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return BUILD_XG_REPORTING_PREVIEW
    if table["preview_valid"].any():
        return XG_REPORTING_PREVIEW_READY
    return FIX_XG_REPORTING_PREVIEW


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    lines = [
        "# Phase 13.16 xG Reporting Preview Audit",
        "",
        "Phase 13.16 is reporting/diagnostic preview only. xG remains inactive in model logic.",
        "",
        "## A. Executive Summary",
        f"- previews audited: {len(table)}",
        f"- valid previews: {int(table['preview_valid'].sum()) if not table.empty else 0}",
        "",
        "## B. Reporting Preview Diagnostics",
    ]
    if table.empty:
        lines += ["No preview files found.", ""]
    else:
        cols = ["preview_file", "row_count", "missing_xg_rows", "non_numeric_xg_rows", "identity_columns_unchanged", "preview_valid", "blocking_reasons"]
        lines += ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
        for _, row in table[cols].iterrows():
            lines.append("| " + " | ".join(str(row[col]).replace("|", ";") for col in cols) + " |")
        lines.append("")
    lines += [
        "## C. Safety Checks",
        "- No target CSV modified in place.",
        "- No accepted artifact modified.",
        "- No production manifest modified.",
        "- No xG values inferred or invented.",
        "- No model, probability, market-tier, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "",
        "## D. Phase 13.16 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(
    *,
    preview: str | Path | None = None,
    preview_dir: str | Path = ROOT / "outputs" / "xg_reporting_preview",
    target: str | Path | None = ROOT / "data" / "processed" / "football_data_D1_2024_clean.csv",
    output_dir: str | Path = ROOT / "outputs" / "diagnostics",
    expected_rows: int | None = 306,
) -> tuple[pd.DataFrame, str, str]:
    target_path = Path(target) if target else None
    rows = [audit_preview_file(path, target=target_path, expected_rows=expected_rows) for path in _preview_paths(preview, preview_dir)]
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
    table, _markdown, rec = run(
        preview=args.preview,
        preview_dir=args.preview_dir,
        target=args.target,
        output_dir=args.output_dir,
        expected_rows=args.expected_rows,
    )
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
