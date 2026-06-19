# -*- coding: utf-8 -*-
"""Audit team-level xG reporting aggregate previews."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

TEAM_XG_REPORTING_AGGREGATES_READY = "TEAM_XG_REPORTING_AGGREGATES_READY"
BUILD_TEAM_XG_REPORTING_AGGREGATES = "BUILD_TEAM_XG_REPORTING_AGGREGATES"
FIX_TEAM_XG_REPORTING_AGGREGATES = "FIX_TEAM_XG_REPORTING_AGGREGATES"

OUTPUT_CSV = "team_xg_reporting_aggregates_summary.csv"
OUTPUT_MD = "team_xg_reporting_aggregates_summary.md"

REQUIRED_COLUMNS = [
    "team",
    "matches",
    "goals_for",
    "goals_against",
    "goal_diff",
    "xg_for",
    "xg_against",
    "xg_diff",
    "goals_minus_xg_for",
    "goals_against_minus_xg_against",
    "points",
    "home_matches",
    "home_goals_for",
    "home_goals_against",
    "home_xg_for",
    "home_xg_against",
    "away_matches",
    "away_goals_for",
    "away_goals_against",
    "away_xg_for",
    "away_xg_against",
    "xg_reporting_status",
]

NUMERIC_XG_COLUMNS = ["xg_for", "xg_against", "xg_diff", "home_xg_for", "home_xg_against", "away_xg_for", "away_xg_against"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", default=None)
    parser.add_argument("--preview-dir", default=str(ROOT / "outputs" / "xg_reporting_preview"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--expected-team-match-rows", type=int, default=612)
    return parser


def _preview_paths(preview: str | Path | None, preview_dir: str | Path) -> list[Path]:
    if preview:
        return [Path(preview)]
    root = Path(preview_dir)
    return sorted(root.glob("*team_xg_reporting_aggregates*.csv")) if root.exists() else []


def audit_aggregate_file(path: Path, *, expected_team_match_rows: int | None = 612) -> dict[str, Any]:
    errors: list[str] = []
    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception as exc:
        return {
            "preview_path": str(path),
            "preview_file": path.name,
            "teams_reported": 0,
            "team_rows_unique": False,
            "team_match_rows": 0,
            "xg_numeric_non_missing": False,
            "missing_status_rows": 0,
            "aggregate_valid": False,
            "blocking_reasons": str(exc),
        }
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        errors.append("MISSING_COLUMNS")
    team_rows_unique = "team" in df.columns and not df["team"].duplicated().any()
    if not team_rows_unique:
        errors.append("DUPLICATE_TEAM_ROWS")
    team_match_rows = int(pd.to_numeric(df["matches"], errors="coerce").sum()) if "matches" in df.columns else 0
    if expected_team_match_rows is not None and team_match_rows != expected_team_match_rows:
        errors.append("UNEXPECTED_TEAM_MATCH_ROWS")
    if set(NUMERIC_XG_COLUMNS).issubset(df.columns):
        numeric = df[NUMERIC_XG_COLUMNS].apply(pd.to_numeric, errors="coerce")
        xg_numeric_non_missing = not numeric.isna().any().any()
    else:
        xg_numeric_non_missing = False
    if not xg_numeric_non_missing:
        errors.append("XG_AGGREGATES_MISSING_OR_NON_NUMERIC")
    missing_status = int(df["xg_reporting_status"].isna().sum()) if "xg_reporting_status" in df.columns else len(df)
    if missing_status:
        errors.append("MISSING_XG_REPORTING_STATUS")
    return {
        "preview_path": str(path),
        "preview_file": path.name,
        "teams_reported": int(len(df)),
        "team_rows_unique": team_rows_unique,
        "team_match_rows": team_match_rows,
        "xg_numeric_non_missing": xg_numeric_non_missing,
        "missing_status_rows": missing_status,
        "aggregate_valid": not errors,
        "blocking_reasons": " | ".join(errors),
    }


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return BUILD_TEAM_XG_REPORTING_AGGREGATES
    if table["aggregate_valid"].any():
        return TEAM_XG_REPORTING_AGGREGATES_READY
    return FIX_TEAM_XG_REPORTING_AGGREGATES


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    lines = [
        "# Phase 13.17 Team xG Reporting Aggregates Audit",
        "",
        "Phase 13.17 is reporting/diagnostic preview only. Team aggregates are not model features.",
        "",
        "## A. Executive Summary",
        f"- aggregate previews audited: {len(table)}",
        f"- valid aggregate previews: {int(table['aggregate_valid'].sum()) if not table.empty else 0}",
        "",
        "## B. Aggregate Diagnostics",
    ]
    if table.empty:
        lines += ["No aggregate previews found.", ""]
    else:
        cols = ["preview_file", "teams_reported", "team_match_rows", "team_rows_unique", "xg_numeric_non_missing", "aggregate_valid", "blocking_reasons"]
        lines += ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
        for _, row in table[cols].iterrows():
            lines.append("| " + " | ".join(str(row[col]).replace("|", ";") for col in cols) + " |")
        lines.append("")
    lines += [
        "## C. Safety Checks",
        "- No source, target, accepted artifact, or production manifest file modified.",
        "- No xG values inferred or invented.",
        "- No model, probability, market-tier, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "",
        "## D. Phase 13.17 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(
    *,
    preview: str | Path | None = None,
    preview_dir: str | Path = ROOT / "outputs" / "xg_reporting_preview",
    output_dir: str | Path = ROOT / "outputs" / "diagnostics",
    expected_team_match_rows: int | None = 612,
) -> tuple[pd.DataFrame, str, str]:
    rows = [audit_aggregate_file(path, expected_team_match_rows=expected_team_match_rows) for path in _preview_paths(preview, preview_dir)]
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
        output_dir=args.output_dir,
        expected_team_match_rows=args.expected_team_match_rows,
    )
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
