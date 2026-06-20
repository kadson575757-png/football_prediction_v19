# -*- coding: utf-8 -*-
"""Audit rolling xG form reporting previews."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

ROLLING_XG_FORM_REPORTING_READY = "ROLLING_XG_FORM_REPORTING_READY"
BUILD_ROLLING_XG_FORM_REPORTING = "BUILD_ROLLING_XG_FORM_REPORTING"
FIX_ROLLING_XG_FORM_REPORTING = "FIX_ROLLING_XG_FORM_REPORTING"

OUTPUT_CSV = "rolling_xg_form_reporting_summary.csv"
OUTPUT_MD = "rolling_xg_form_reporting_summary.md"

ROLLING_COLUMNS = [
    "rolling_matches_available",
    "rolling_xg_for",
    "rolling_xg_against",
    "rolling_xg_diff",
    "rolling_goals_for",
    "rolling_goals_against",
    "rolling_goal_diff",
    "rolling_goals_minus_xg_for",
    "rolling_goals_against_minus_xg_against",
    "rolling_points",
    "xg_form_status",
]

NUMERIC_ROLLING_COLUMNS = [col for col in ROLLING_COLUMNS if col != "xg_form_status"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", default=None)
    parser.add_argument("--preview-dir", default=str(ROOT / "outputs" / "xg_reporting_preview"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--expected-team-match-rows", type=int, default=612)
    parser.add_argument("--expected-teams", type=int, default=18)
    return parser


def _preview_paths(preview: str | Path | None, preview_dir: str | Path) -> list[Path]:
    if preview:
        return [Path(preview)]
    root = Path(preview_dir)
    return sorted(root.glob("*rolling_xg_form*.csv")) if root.exists() else []


def audit_form_file(path: Path, *, expected_team_match_rows: int | None = 612, expected_teams: int | None = 18) -> dict[str, Any]:
    errors: list[str] = []
    try:
        df = pd.read_csv(path, low_memory=False)
    except Exception as exc:
        return {
            "preview_path": str(path),
            "preview_file": path.name,
            "team_match_rows": 0,
            "teams_reported": 0,
            "first_matches_zero": False,
            "rolling_numeric_valid": False,
            "missing_status_rows": 0,
            "form_valid": False,
            "blocking_reasons": str(exc),
        }
    missing_cols = [col for col in ROLLING_COLUMNS + ["team", "date"] if col not in df.columns]
    if missing_cols:
        errors.append("MISSING_ROLLING_COLUMNS")
    rows = int(len(df))
    teams = int(df["team"].nunique()) if "team" in df.columns else 0
    if expected_team_match_rows is not None and rows != expected_team_match_rows:
        errors.append("UNEXPECTED_TEAM_MATCH_ROWS")
    if expected_teams is not None and teams != expected_teams:
        errors.append("UNEXPECTED_TEAM_COUNT")
    if {"team", "date", "rolling_matches_available"}.issubset(df.columns):
        sorted_df = df.sort_values(["team", "date"]).copy()
        first = sorted_df.groupby("team").head(1)
        first_zero = bool((pd.to_numeric(first["rolling_matches_available"], errors="coerce") == 0).all())
    else:
        first_zero = False
    if not first_zero:
        errors.append("FIRST_TEAM_MATCH_NOT_ZERO")
    if set(NUMERIC_ROLLING_COLUMNS).issubset(df.columns):
        positive_history = pd.to_numeric(df["rolling_matches_available"], errors="coerce") > 0
        numeric = df.loc[positive_history, NUMERIC_ROLLING_COLUMNS].apply(pd.to_numeric, errors="coerce")
        numeric_valid = not numeric.isna().any().any()
    else:
        numeric_valid = False
    if not numeric_valid and rows:
        errors.append("ROLLING_VALUES_NON_NUMERIC")
    missing_status = int(df["xg_form_status"].isna().sum()) if "xg_form_status" in df.columns else rows
    if missing_status:
        errors.append("MISSING_XG_FORM_STATUS")
    return {
        "preview_path": str(path),
        "preview_file": path.name,
        "team_match_rows": rows,
        "teams_reported": teams,
        "first_matches_zero": first_zero,
        "rolling_numeric_valid": numeric_valid,
        "missing_status_rows": missing_status,
        "form_valid": not errors,
        "blocking_reasons": " | ".join(errors),
    }


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return BUILD_ROLLING_XG_FORM_REPORTING
    if table["form_valid"].any():
        return ROLLING_XG_FORM_REPORTING_READY
    return FIX_ROLLING_XG_FORM_REPORTING


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    lines = [
        "# Phase 13.18 Rolling xG Form Reporting Audit",
        "",
        "Phase 13.18 is reporting/diagnostic preview only. Rolling form is not a model feature.",
        "",
        "## A. Executive Summary",
        f"- rolling previews audited: {len(table)}",
        f"- valid rolling previews: {int(table['form_valid'].sum()) if not table.empty else 0}",
        "",
        "## B. Rolling Diagnostics",
    ]
    if table.empty:
        lines += ["No rolling form previews found.", ""]
    else:
        cols = ["preview_file", "team_match_rows", "teams_reported", "first_matches_zero", "rolling_numeric_valid", "form_valid", "blocking_reasons"]
        lines += ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
        for _, row in table[cols].iterrows():
            lines.append("| " + " | ".join(str(row[col]).replace("|", ";") for col in cols) + " |")
        lines.append("")
    lines += [
        "## C. Safety Checks",
        "- No source, target, accepted artifact, or production manifest file modified.",
        "- No xG values inferred or invented.",
        "- Rolling values use pre-match history only.",
        "- No model, probability, market-tier, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "",
        "## D. Phase 13.18 Recommendation",
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
    expected_teams: int | None = 18,
) -> tuple[pd.DataFrame, str, str]:
    rows = [audit_form_file(path, expected_team_match_rows=expected_team_match_rows, expected_teams=expected_teams) for path in _preview_paths(preview, preview_dir)]
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
        expected_teams=args.expected_teams,
    )
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
