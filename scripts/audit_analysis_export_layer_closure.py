# -*- coding: utf-8 -*-
"""Audit closure of the analysis export usability layer."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_analysis_excel_workbook_preview import ANALYSIS_EXCEL_WORKBOOK_PREVIEW_READY, run as run_excel_audit  # noqa: E402
from audit_analysis_export_bundle_preview import ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY, run as run_bundle_audit  # noqa: E402
from audit_manifest_xg_readiness import MANIFEST_XG_READINESS_READY, run as run_manifest_audit  # noqa: E402
from audit_xg_reporting_layer_closure import (  # noqa: E402
    XG_MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN,
    XG_REPORTING_LAYER_COMPLETE,
    run as run_xg_closure,
)
from audit_xg_reporting_pack_preview import XG_REPORTING_PACK_PREVIEW_READY, run as run_pack_audit  # noqa: E402
from build_analysis_excel_workbook_preview import build_analysis_excel_workbook_preview  # noqa: E402

ANALYSIS_EXPORT_LAYER_COMPLETE = "ANALYSIS_EXPORT_LAYER_COMPLETE"
ANALYSIS_EXPORT_LAYER_PARTIAL = "ANALYSIS_EXPORT_LAYER_PARTIAL"
ANALYSIS_EXPORT_LAYER_BLOCKED = "ANALYSIS_EXPORT_LAYER_BLOCKED"

ANALYSIS_EXPORT_LAYER_COMPLETE_READY_FOR_HUMAN_ANALYSIS = "ANALYSIS_EXPORT_LAYER_COMPLETE_READY_FOR_HUMAN_ANALYSIS"
FIX_ANALYSIS_EXPORT_LAYER = "FIX_ANALYSIS_EXPORT_LAYER"
BUILD_ANALYSIS_EXCEL_WORKBOOK_PREVIEW = "BUILD_ANALYSIS_EXCEL_WORKBOOK_PREVIEW"
BUILD_ANALYSIS_EXPORT_BUNDLE_PREVIEW = "BUILD_ANALYSIS_EXPORT_BUNDLE_PREVIEW"

OUTPUT_CSV = "analysis_export_layer_closure_summary.csv"
OUTPUT_MD = "analysis_export_layer_closure_summary.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(ROOT / "data" / "templates" / "manual_xg_manifest_template.csv"))
    parser.add_argument("--manifest-id", default="trusted_xg_understat_bundesliga_2024_manual_xg")
    parser.add_argument("--window", type=int, default=5)
    parser.add_argument("--preview-dir", default=str(ROOT / "outputs" / "analysis_export_preview"))
    parser.add_argument("--xg-preview-dir", default=str(ROOT / "outputs" / "xg_reporting_preview"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    parser.add_argument("--no-build", action="store_true")
    return parser


def _row(check_name: str, status: str, recommendation: str, details: str, blocking: bool) -> dict[str, Any]:
    return {
        "check_name": check_name,
        "status": status,
        "recommendation": recommendation,
        "details": details,
        "blocking": bool(blocking),
        "model_integration_status": XG_MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN,
    }


def _first_detail(table: pd.DataFrame, *cols: str) -> str:
    if table.empty:
        return ""
    parts = []
    for col in cols:
        if col in table.columns:
            parts.append(f"{col}={table.iloc[0][col]}")
    return "; ".join(parts)


def _ensure_outputs(
    *,
    manifest: Path,
    manifest_id: str | None,
    window: int,
    preview_dir: Path,
    xg_preview_dir: Path,
    output_dir: Path,
    base_dir: Path,
    no_build: bool,
) -> dict[str, Any]:
    if no_build:
        return {}
    run_xg_closure(
        manifest=manifest,
        manifest_id=manifest_id,
        window=window,
        preview_dir=xg_preview_dir,
        output_dir=output_dir,
        base_dir=base_dir,
    )
    return build_analysis_excel_workbook_preview(
        manifest=manifest,
        manifest_id=manifest_id,
        window=window,
        output_dir=preview_dir,
        write_preview=True,
        base_dir=base_dir,
    )


def _closure_status(rows: list[dict[str, Any]]) -> str:
    blocking = [row for row in rows if row["blocking"]]
    if not blocking:
        return ANALYSIS_EXPORT_LAYER_COMPLETE
    ready_count = sum(not row["blocking"] for row in rows)
    return ANALYSIS_EXPORT_LAYER_PARTIAL if ready_count else ANALYSIS_EXPORT_LAYER_BLOCKED


def _final_recommendation(rows: list[dict[str, Any]], status: str) -> str:
    by_name = {row["check_name"]: row for row in rows}
    if by_name.get("excel_workbook", {}).get("recommendation") == BUILD_ANALYSIS_EXCEL_WORKBOOK_PREVIEW:
        return BUILD_ANALYSIS_EXCEL_WORKBOOK_PREVIEW
    if by_name.get("analysis_export_bundle", {}).get("recommendation") == BUILD_ANALYSIS_EXPORT_BUNDLE_PREVIEW:
        return BUILD_ANALYSIS_EXPORT_BUNDLE_PREVIEW
    if status == ANALYSIS_EXPORT_LAYER_COMPLETE:
        return ANALYSIS_EXPORT_LAYER_COMPLETE_READY_FOR_HUMAN_ANALYSIS
    return FIX_ANALYSIS_EXPORT_LAYER


def build_markdown(table: pd.DataFrame, export_status: str, rec: str, manifest_id: str) -> str:
    lines = [
        "# Phase 14.3 Analysis Export Layer Closure Audit",
        "",
        "Phase 14.3 is a closure/export/reporting audit only. xG remains inactive in model logic by design.",
        "",
        "## A. Executive Summary",
        f"- manifest_id: {manifest_id}",
        f"- export_layer_status: {export_status}",
        f"- model_integration_status: {XG_MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN}",
        f"- recommendation: {rec}",
        "",
        "## B. Closure Checks",
    ]
    if table.empty:
        lines += ["No closure checks were produced.", ""]
    else:
        cols = ["check_name", "status", "recommendation", "blocking", "details"]
        lines += ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
        for _, row in table[cols].iterrows():
            lines.append("| " + " | ".join(str(row[col]).replace("|", ";") for col in cols) + " |")
        lines.append("")
    lines += [
        "## C. Safety Checks",
        "- No xG values inferred or invented.",
        "- No target CSV modified in place.",
        "- No accepted xG artifact modified.",
        "- No raw Understat source CSV modified.",
        "- No production manifest modified.",
        "- No model feature activation.",
        "- No prediction, probability, market ranking, recommended-market, betting, staking, ROI, stake sizing, or SUPER_A_TIER logic changed.",
        "",
        "## D. Phase 14.3 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(
    *,
    manifest: str | Path = ROOT / "data" / "templates" / "manual_xg_manifest_template.csv",
    manifest_id: str | None = "trusted_xg_understat_bundesliga_2024_manual_xg",
    window: int = 5,
    preview_dir: str | Path = ROOT / "outputs" / "analysis_export_preview",
    xg_preview_dir: str | Path = ROOT / "outputs" / "xg_reporting_preview",
    output_dir: str | Path = ROOT / "outputs" / "diagnostics",
    base_dir: str | Path = ROOT,
    no_build: bool = False,
) -> tuple[pd.DataFrame, str, str]:
    base = Path(base_dir).resolve()
    preview = Path(preview_dir)
    if not preview.is_absolute():
        preview = base / preview
    xg_preview = Path(xg_preview_dir)
    if not xg_preview.is_absolute():
        xg_preview = base / xg_preview
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    manifest_path = Path(manifest)
    if not manifest_path.is_absolute():
        manifest_path = base / manifest_path

    excel_summary = _ensure_outputs(
        manifest=manifest_path,
        manifest_id=manifest_id,
        window=window,
        preview_dir=preview,
        xg_preview_dir=xg_preview,
        output_dir=out,
        base_dir=base,
        no_build=no_build,
    )
    workbook_path = excel_summary.get("workbook_path") if excel_summary else None
    bundle_index = preview / str(manifest_id or "") / "analysis_export_bundle_index.csv"

    rows: list[dict[str, Any]] = []
    excel_table, _excel_md, excel_rec = run_excel_audit(workbook=workbook_path or None, preview_dir=preview, output_dir=out, base_dir=base)
    if excel_rec == "BUILD_ANALYSIS_EXCEL_WORKBOOK_PREVIEW":
        excel_status = "BUILD_ANALYSIS_EXCEL_WORKBOOK_PREVIEW"
    else:
        excel_status = excel_rec
    rows.append(_row("excel_workbook", excel_status, excel_rec, _first_detail(excel_table, "sheets_found", "model_integration_status"), excel_rec != ANALYSIS_EXCEL_WORKBOOK_PREVIEW_READY))

    bundle_table, _bundle_md, bundle_rec = run_bundle_audit(index=bundle_index if bundle_index.exists() else None, preview_dir=preview, output_dir=out, base_dir=base)
    rows.append(_row("analysis_export_bundle", bundle_rec, bundle_rec, _first_detail(bundle_table, "exports_found", "exports_ready"), bundle_rec != ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY))

    xg_table, _xg_md, xg_rec = run_xg_closure(manifest=manifest_path, manifest_id=manifest_id, window=window, preview_dir=xg_preview, output_dir=out, base_dir=base, no_build=no_build)
    xg_status = "XG_REPORTING_LAYER_COMPLETE" if xg_rec == "XG_REPORTING_LAYER_COMPLETE_READY_FOR_HUMAN_DIAGNOSTICS" else xg_rec
    rows.append(_row("xg_reporting_layer_closure", xg_status, xg_rec, _first_detail(xg_table, "status", "recommendation"), xg_status != XG_REPORTING_LAYER_COMPLETE))

    pack_table, _pack_md, pack_rec = run_pack_audit(preview_dir=xg_preview, output_dir=out, base_dir=base)
    rows.append(_row("xg_reporting_pack", pack_rec, pack_rec, _first_detail(pack_table, "reports_found", "reports_ready"), pack_rec != XG_REPORTING_PACK_PREVIEW_READY))

    manifest_table, _manifest_md, manifest_rec = run_manifest_audit(manifest=manifest_path, manifest_id=manifest_id, output_dir=out, base_dir=base)
    rows.append(_row("manifest_xg_readiness", manifest_rec, manifest_rec, _first_detail(manifest_table, "readiness_status", "join_coverage_pct"), manifest_rec != MANIFEST_XG_READINESS_READY))

    export_status = _closure_status(rows)
    rec = _final_recommendation(rows, export_status)
    table = pd.DataFrame(rows)
    markdown = build_markdown(table, export_status, rec, manifest_id or "")
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / OUTPUT_CSV, index=False)
    (out / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown, rec


def summarize_export_layer(table: pd.DataFrame, rec: str) -> dict[str, Any]:
    status = _closure_status(table.to_dict("records")) if not table.empty else ANALYSIS_EXPORT_LAYER_BLOCKED
    by_name = {row["check_name"]: row for row in table.to_dict("records")} if not table.empty else {}
    return {
        "export_layer_status": status,
        "export_bundle_status": by_name.get("analysis_export_bundle", {}).get("status", ""),
        "excel_workbook_status": by_name.get("excel_workbook", {}).get("status", ""),
        "xg_reporting_layer_status": by_name.get("xg_reporting_layer_closure", {}).get("status", ""),
        "model_integration_status": XG_MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN,
        "recommendation": rec,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, _markdown, rec = run(
        manifest=args.manifest,
        manifest_id=args.manifest_id,
        window=args.window,
        preview_dir=args.preview_dir,
        xg_preview_dir=args.xg_preview_dir,
        output_dir=args.output_dir,
        base_dir=args.base_dir,
        no_build=args.no_build,
    )
    summary = summarize_export_layer(table, rec)
    for key in [
        "export_layer_status",
        "export_bundle_status",
        "excel_workbook_status",
        "xg_reporting_layer_status",
        "model_integration_status",
        "recommendation",
    ]:
        print(f"{key}={summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
