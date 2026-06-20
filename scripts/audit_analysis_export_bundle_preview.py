# -*- coding: utf-8 -*-
"""Audit Phase 14.1 analysis export bundle previews."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY = "ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY"
BUILD_ANALYSIS_EXPORT_BUNDLE_PREVIEW = "BUILD_ANALYSIS_EXPORT_BUNDLE_PREVIEW"
FIX_ANALYSIS_EXPORT_BUNDLE_PREVIEW = "FIX_ANALYSIS_EXPORT_BUNDLE_PREVIEW"

OUTPUT_CSV = "analysis_export_bundle_preview_summary.csv"
OUTPUT_MD = "analysis_export_bundle_preview_summary.md"

EXPECTED_EXPORTS = [
    "match_level_xg_reporting_preview.csv",
    "team_xg_reporting_aggregates.csv",
    "rolling_xg_form_reporting.csv",
    "xg_matchup_reporting_preview.csv",
    "xg_reporting_pack_index.csv",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", default=None)
    parser.add_argument("--preview-dir", default=str(ROOT / "outputs" / "analysis_export_preview"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _find_indexes(index: str | Path | None, preview_dir: str | Path) -> list[Path]:
    if index:
        return [Path(index)]
    root = Path(preview_dir)
    return sorted(root.glob("*/analysis_export_bundle_index.csv")) if root.exists() else []


def _under_export_preview(path_text: str, base: Path) -> bool:
    if not path_text:
        return False
    path = Path(path_text)
    if not path.is_absolute():
        path = base / path
    try:
        resolved = path.resolve()
    except OSError:
        return False
    allowed = (base / "outputs" / "analysis_export_preview").resolve()
    return resolved == allowed or allowed in resolved.parents


def _forbidden_path(path_text: str) -> bool:
    normalized = str(path_text).replace("\\", "/").lower()
    forbidden = [
        "/data/processed/",
        "/data/templates/",
        "/data/trusted_xg_sources/accepted/",
        "/data/trusted_xg_sources/raw/",
    ]
    return any(fragment in normalized for fragment in forbidden)


def audit_index(index_path: Path, *, base_dir: str | Path = ROOT) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    errors: list[str] = []
    try:
        table = pd.read_csv(index_path, low_memory=False)
    except Exception as exc:
        return {
            "index_path": str(index_path),
            "manifest_id": "",
            "exports_found": 0,
            "exports_ready": 0,
            "missing_exports": "ALL",
            "zero_row_exports": "",
            "unsafe_output_paths": "",
            "forbidden_output_paths": "",
            "model_integration_status": "",
            "bundle_valid": False,
            "blocking_reasons": str(exc),
        }
    required_cols = {"manifest_id", "export_name", "source_report_type", "source_status", "rows", "output_path", "export_status", "recommendation"}
    if not required_cols.issubset(table.columns):
        errors.append("MISSING_INDEX_COLUMNS")
    found = set(table["export_name"].astype(str)) if "export_name" in table.columns else set()
    missing = [name for name in EXPECTED_EXPORTS if name not in found]
    if missing:
        errors.append("MISSING_EXPECTED_EXPORTS")
    paths = table["output_path"].fillna("").astype(str).tolist() if "output_path" in table.columns else []
    unsafe = [path for path in paths if not _under_export_preview(path, base)]
    forbidden = [path for path in paths if _forbidden_path(path)]
    if unsafe:
        errors.append("UNSAFE_OUTPUT_PATH")
    if forbidden:
        errors.append("FORBIDDEN_PRODUCTION_OUTPUT_PATH")
    zero_rows: list[str] = []
    if {"export_name", "rows"}.issubset(table.columns):
        for _, row in table[table["export_name"].isin(EXPECTED_EXPORTS)].iterrows():
            if int(row["rows"]) <= 0:
                zero_rows.append(str(row["export_name"]))
    if zero_rows:
        errors.append("ZERO_ROW_EXPORT")
    missing_files = [path for path in paths if path and not Path(path).exists()]
    if missing_files:
        errors.append("EXPORT_FILE_MISSING")
    model_status = ""
    closure_rows = table[table["export_name"].astype(str).eq("xg_reporting_layer_closure_summary.csv")] if "export_name" in table.columns else pd.DataFrame()
    if not closure_rows.empty:
        closure_path = Path(str(closure_rows.iloc[0]["output_path"]))
        if closure_path.exists():
            closure = pd.read_csv(closure_path, low_memory=False)
            if "model_integration_status" in closure.columns and not closure.empty:
                model_status = str(closure["model_integration_status"].iloc[0])
                if model_status != "XG_MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN":
                    errors.append("MODEL_INTEGRATION_STATUS_NOT_SAFE")
    ready_count = int(table["export_status"].astype(str).eq("EXPORT_READY").sum()) if "export_status" in table.columns else 0
    return {
        "index_path": str(index_path),
        "manifest_id": str(table["manifest_id"].iloc[0]) if "manifest_id" in table.columns and not table.empty else "",
        "exports_found": int(len(table)),
        "exports_ready": ready_count,
        "missing_exports": " | ".join(missing),
        "zero_row_exports": " | ".join(zero_rows),
        "unsafe_output_paths": " | ".join(unsafe),
        "forbidden_output_paths": " | ".join(forbidden),
        "model_integration_status": model_status,
        "bundle_valid": not errors,
        "blocking_reasons": " | ".join(errors),
    }


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return BUILD_ANALYSIS_EXPORT_BUNDLE_PREVIEW
    if table["bundle_valid"].any():
        return ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY
    return FIX_ANALYSIS_EXPORT_BUNDLE_PREVIEW


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    lines = [
        "# Phase 14.1 Analysis Export Bundle Preview Audit",
        "",
        "Phase 14.1 is an export/reporting preview only. xG remains inactive in model logic.",
        "",
        "## A. Executive Summary",
        f"- bundles audited: {len(table)}",
        f"- valid bundles: {int(table['bundle_valid'].sum()) if not table.empty else 0}",
        "",
        "## B. Bundle Diagnostics",
    ]
    if table.empty:
        lines += ["No analysis export bundle indexes found.", ""]
    else:
        cols = ["manifest_id", "exports_found", "exports_ready", "missing_exports", "zero_row_exports", "bundle_valid", "blocking_reasons"]
        lines += ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
        for _, row in table[cols].iterrows():
            lines.append("| " + " | ".join(str(row[col]).replace("|", ";") for col in cols) + " |")
        lines.append("")
    lines += [
        "## C. Safety Checks",
        "- All export paths must stay under outputs/analysis_export_preview.",
        "- No export path may point to production targets, manifests, accepted artifacts, or raw trusted sources.",
        "- No xG values inferred or invented.",
        "- No model, probability, market-tier, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "",
        "## D. Phase 14.1 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(
    *,
    index: str | Path | None = None,
    preview_dir: str | Path = ROOT / "outputs" / "analysis_export_preview",
    output_dir: str | Path = ROOT / "outputs" / "diagnostics",
    base_dir: str | Path = ROOT,
) -> tuple[pd.DataFrame, str, str]:
    rows = [audit_index(path, base_dir=base_dir) for path in _find_indexes(index, preview_dir)]
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
