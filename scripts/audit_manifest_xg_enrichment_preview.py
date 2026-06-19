# -*- coding: utf-8 -*-
"""Audit manifest-backed xG enrichment previews."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

MANIFEST_XG_ENRICHMENT_PREVIEW_READY = "MANIFEST_XG_ENRICHMENT_PREVIEW_READY"
BUILD_MANIFEST_XG_ENRICHMENT_PREVIEW = "BUILD_MANIFEST_XG_ENRICHMENT_PREVIEW"
FIX_MANIFEST_XG_ENRICHMENT_PREVIEW = "FIX_MANIFEST_XG_ENRICHMENT_PREVIEW"

OUTPUT_CSV = "manifest_xg_enrichment_preview_summary.csv"
OUTPUT_MD = "manifest_xg_enrichment_preview_summary.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", default=None)
    parser.add_argument("--preview-dir", default=str(ROOT / "outputs" / "xg_enrichment_preview"))
    parser.add_argument("--target", default=str(ROOT / "data" / "processed" / "football_data_D1_2024_clean.csv"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--expected-rows", type=int, default=306)
    return parser


def _identity_columns(df: pd.DataFrame) -> list[str]:
    candidates = ["Date", "date", "HomeTeam", "home_team", "AwayTeam", "away_team", "FTHG", "FTAG", "FTR"]
    return [col for col in candidates if col in df.columns]


def _preview_paths(preview: str | Path | None, preview_dir: str | Path) -> list[Path]:
    if preview:
        return [Path(preview)]
    root = Path(preview_dir)
    if not root.exists():
        return []
    return sorted(root.glob("*.csv"))


def audit_preview_file(path: Path, *, target: Path | None = None, expected_rows: int | None = None) -> dict[str, Any]:
    errors: list[str] = []
    try:
        preview = pd.read_csv(path, low_memory=False)
    except Exception as exc:
        return {
            "preview_path": str(path),
            "preview_file": path.name,
            "row_count": 0,
            "has_xg_columns": False,
            "missing_xg_rows": 0,
            "identity_columns_unchanged": False,
            "preview_valid": False,
            "blocking_reasons": str(exc),
        }
    has_xg = {"home_xg", "away_xg"}.issubset(preview.columns)
    if not has_xg:
        errors.append("MISSING_XG_COLUMNS")
        missing_xg = len(preview)
    else:
        missing_xg = int(preview[["home_xg", "away_xg"]].isna().any(axis=1).sum())
        if missing_xg:
            errors.append("MISSING_XG_VALUES")
    if expected_rows is not None and len(preview) != expected_rows:
        errors.append("UNEXPECTED_ROW_COUNT")
    identity_unchanged = False
    if target is not None and target.exists():
        target_df = pd.read_csv(target, low_memory=False)
        cols = _identity_columns(target_df)
        identity_unchanged = bool(cols) and len(target_df) == len(preview) and preview[cols].equals(target_df[cols])
        if not identity_unchanged:
            errors.append("TARGET_IDENTITY_COLUMNS_CHANGED")
    elif target is None:
        identity_unchanged = True
    else:
        errors.append("TARGET_NOT_FOUND")
    return {
        "preview_path": str(path),
        "preview_file": path.name,
        "row_count": int(len(preview)),
        "has_xg_columns": has_xg,
        "missing_xg_rows": missing_xg,
        "identity_columns_unchanged": identity_unchanged,
        "preview_valid": not errors,
        "blocking_reasons": " | ".join(errors),
    }


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return BUILD_MANIFEST_XG_ENRICHMENT_PREVIEW
    if table["preview_valid"].any():
        return MANIFEST_XG_ENRICHMENT_PREVIEW_READY
    return FIX_MANIFEST_XG_ENRICHMENT_PREVIEW


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    valid_count = int(table["preview_valid"].sum()) if not table.empty else 0
    lines = [
        "# Phase 13.14 Manifest xG Enrichment Preview Audit",
        "",
        "Phase 13.14 is diagnostic/foundation only. Preview CSVs are not model inputs and xG remains inactive.",
        "",
        "## A. Executive Summary",
        f"- previews audited: {len(table)}",
        f"- valid previews: {valid_count}",
        "",
        "## B. Preview Diagnostics",
    ]
    if table.empty:
        lines += ["No preview files found.", ""]
    else:
        cols = ["preview_file", "row_count", "has_xg_columns", "missing_xg_rows", "identity_columns_unchanged", "preview_valid", "blocking_reasons"]
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
        "## D. Phase 13.14 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(
    *,
    preview: str | Path | None = None,
    preview_dir: str | Path = ROOT / "outputs" / "xg_enrichment_preview",
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
