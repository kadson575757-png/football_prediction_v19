# -*- coding: utf-8 -*-
"""Audit xG reporting pack preview indexes."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

XG_REPORTING_PACK_PREVIEW_READY = "XG_REPORTING_PACK_PREVIEW_READY"
BUILD_XG_REPORTING_PACK_PREVIEW = "BUILD_XG_REPORTING_PACK_PREVIEW"
FIX_XG_REPORTING_PACK_PREVIEW = "FIX_XG_REPORTING_PACK_PREVIEW"

OUTPUT_CSV = "xg_reporting_pack_preview_summary.csv"
OUTPUT_MD = "xg_reporting_pack_preview_summary.md"

EXPECTED_READY = {
    "match_level_reporting_preview": "XG_REPORTING_PREVIEW_READY",
    "team_xg_reporting_aggregates": "TEAM_XG_REPORTING_AGGREGATES_READY",
    "rolling_xg_form_reporting": "ROLLING_XG_FORM_REPORTING_READY",
    "xg_matchup_reporting_preview": "XG_MATCHUP_REPORTING_PREVIEW_READY",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", default=None)
    parser.add_argument("--preview-dir", default=str(ROOT / "outputs" / "xg_reporting_preview"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _default_index(preview_dir: str | Path) -> Path | None:
    path = Path(preview_dir) / "xg_reporting_pack_index.csv"
    return path if path.exists() else None


def _under_outputs_xg_reporting(path_text: str, base: Path) -> bool:
    if not path_text:
        return False
    path = Path(path_text)
    if not path.is_absolute():
        path = base / path
    try:
        resolved = path.resolve()
    except OSError:
        return False
    allowed = (base / "outputs" / "xg_reporting_preview").resolve()
    return resolved == allowed or allowed in resolved.parents


def _forbidden_path(path_text: str) -> bool:
    normalized = str(path_text).replace("\\", "/").lower()
    forbidden_fragments = [
        "/data/processed/",
        "/data/templates/",
        "/data/trusted_xg_sources/accepted/",
        "/data/trusted_xg_sources/raw/",
    ]
    return any(fragment in normalized for fragment in forbidden_fragments)


def audit_pack_index(index_path: Path, *, base_dir: str | Path = ROOT) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    try:
        df = pd.read_csv(index_path, low_memory=False)
    except Exception as exc:
        return {
            "index_path": str(index_path),
            "reports_found": 0,
            "reports_ready": 0,
            "missing_report_types": "ALL",
            "non_ready_report_types": "ALL",
            "unsafe_output_paths": "",
            "forbidden_output_paths": "",
            "pack_valid": False,
            "blocking_reasons": str(exc),
        }
    required_cols = {"manifest_id", "report_type", "status", "rows", "output_path", "recommendation"}
    errors: list[str] = []
    if not required_cols.issubset(df.columns):
        errors.append("MISSING_INDEX_COLUMNS")
    found = set(df["report_type"].astype(str)) if "report_type" in df.columns else set()
    missing = [report for report in EXPECTED_READY if report not in found]
    if missing:
        errors.append("MISSING_REPORT_TYPES")
    non_ready: list[str] = []
    if {"report_type", "status"}.issubset(df.columns):
        for report, ready in EXPECTED_READY.items():
            statuses = df.loc[df["report_type"].astype(str).eq(report), "status"].astype(str).tolist()
            if not statuses or ready not in statuses:
                non_ready.append(report)
    if non_ready:
        errors.append("REPORT_NOT_READY")
    output_paths = df["output_path"].fillna("").astype(str).tolist() if "output_path" in df.columns else []
    unsafe = [path for path in output_paths if not _under_outputs_xg_reporting(path, base)]
    forbidden = [path for path in output_paths if _forbidden_path(path)]
    if unsafe:
        errors.append("UNSAFE_OUTPUT_PATH")
    if forbidden:
        errors.append("FORBIDDEN_PRODUCTION_OUTPUT_PATH")
    return {
        "index_path": str(index_path),
        "reports_found": int(len(df)),
        "reports_ready": int(sum(df["status"].astype(str).isin(EXPECTED_READY.values()))) if "status" in df.columns else 0,
        "missing_report_types": " | ".join(missing),
        "non_ready_report_types": " | ".join(non_ready),
        "unsafe_output_paths": " | ".join(unsafe),
        "forbidden_output_paths": " | ".join(forbidden),
        "pack_valid": not errors,
        "blocking_reasons": " | ".join(errors),
    }


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return BUILD_XG_REPORTING_PACK_PREVIEW
    if table["pack_valid"].any():
        return XG_REPORTING_PACK_PREVIEW_READY
    return FIX_XG_REPORTING_PACK_PREVIEW


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    lines = [
        "# Phase 13.20 xG Reporting Pack Preview Audit",
        "",
        "Phase 13.20 is reporting/diagnostic preview only. xG is not active in model logic.",
        "",
        "## A. Executive Summary",
        f"- pack indexes audited: {len(table)}",
        f"- valid pack indexes: {int(table['pack_valid'].sum()) if not table.empty else 0}",
        "",
        "## B. Pack Diagnostics",
    ]
    if table.empty:
        lines += ["No reporting pack index found.", ""]
    else:
        cols = ["reports_found", "reports_ready", "missing_report_types", "non_ready_report_types", "pack_valid", "blocking_reasons"]
        lines += ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
        for _, row in table[cols].iterrows():
            lines.append("| " + " | ".join(str(row[col]).replace("|", ";") for col in cols) + " |")
        lines.append("")
    lines += [
        "## C. Safety Checks",
        "- All report output paths must stay under outputs/xg_reporting_preview.",
        "- No output path may point to a production target, production manifest, accepted artifact, or raw trusted source.",
        "- No xG values inferred or invented.",
        "- No model, probability, market-tier, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "",
        "## D. Phase 13.20 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(
    *,
    index: str | Path | None = None,
    preview_dir: str | Path = ROOT / "outputs" / "xg_reporting_preview",
    output_dir: str | Path = ROOT / "outputs" / "diagnostics",
    base_dir: str | Path = ROOT,
) -> tuple[pd.DataFrame, str, str]:
    index_path = Path(index) if index else _default_index(preview_dir)
    rows = [audit_pack_index(index_path, base_dir=base_dir)] if index_path else []
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
    table, _markdown, rec = run(index=args.index, preview_dir=args.preview_dir, output_dir=args.output_dir, base_dir=args.base_dir)
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
