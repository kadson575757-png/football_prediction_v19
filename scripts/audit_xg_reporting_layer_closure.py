# -*- coding: utf-8 -*-
"""Audit closure of the reporting-only xG layer."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_manifest_xg_readiness import MANIFEST_XG_READINESS_READY, run as run_manifest_readiness  # noqa: E402
from audit_rolling_xg_form_reporting import ROLLING_XG_FORM_REPORTING_READY, run as run_rolling_audit  # noqa: E402
from audit_team_xg_reporting_aggregates import TEAM_XG_REPORTING_AGGREGATES_READY, run as run_team_audit  # noqa: E402
from audit_xg_matchup_reporting_preview import XG_MATCHUP_REPORTING_PREVIEW_READY, run as run_matchup_audit  # noqa: E402
from audit_xg_reporting_pack_preview import XG_REPORTING_PACK_PREVIEW_READY, run as run_pack_audit  # noqa: E402
from audit_xg_reporting_preview import XG_REPORTING_PREVIEW_READY, run as run_reporting_audit  # noqa: E402
from build_xg_reporting_pack_preview import build_xg_reporting_pack_preview  # noqa: E402

XG_REPORTING_LAYER_COMPLETE = "XG_REPORTING_LAYER_COMPLETE"
XG_REPORTING_LAYER_BLOCKED = "XG_REPORTING_LAYER_BLOCKED"
XG_REPORTING_LAYER_PARTIAL = "XG_REPORTING_LAYER_PARTIAL"

XG_MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN = "XG_MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN"

XG_REPORTING_LAYER_COMPLETE_READY_FOR_HUMAN_DIAGNOSTICS = "XG_REPORTING_LAYER_COMPLETE_READY_FOR_HUMAN_DIAGNOSTICS"
FIX_XG_REPORTING_LAYER = "FIX_XG_REPORTING_LAYER"
BUILD_XG_REPORTING_PACK_PREVIEW = "BUILD_XG_REPORTING_PACK_PREVIEW"

OUTPUT_CSV = "xg_reporting_layer_closure_summary.csv"
OUTPUT_MD = "xg_reporting_layer_closure_summary.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(ROOT / "data" / "templates" / "manual_xg_manifest_template.csv"))
    parser.add_argument("--manifest-id", default=None)
    parser.add_argument("--window", type=int, default=5)
    parser.add_argument("--preview-dir", default=str(ROOT / "outputs" / "xg_reporting_preview"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    parser.add_argument("--no-build", action="store_true")
    return parser


def _ensure_pack(
    *,
    manifest: str | Path,
    manifest_id: str | None,
    window: int,
    preview_dir: Path,
    base_dir: Path,
    no_build: bool,
) -> dict[str, Any]:
    index = preview_dir / "xg_reporting_pack_index.csv"
    if index.exists() or no_build:
        return {
            "reporting_pack_status": "",
            "manifest_id": manifest_id or "",
            "reports_ready": 0,
            "reporting_pack_index_path": str(index) if index.exists() else "",
        }
    return build_xg_reporting_pack_preview(
        manifest=manifest,
        manifest_id=manifest_id,
        window=window,
        output_dir=preview_dir,
        write_preview=True,
        base_dir=base_dir,
    )


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


def _pack_path(preview_dir: Path, report_type: str) -> str | None:
    index = preview_dir / "xg_reporting_pack_index.csv"
    if not index.exists():
        return None
    try:
        table = pd.read_csv(index, low_memory=False)
    except Exception:
        return None
    if not {"report_type", "output_path"}.issubset(table.columns):
        return None
    rows = table[table["report_type"].astype(str).eq(report_type)]
    if rows.empty:
        return None
    path = str(rows.iloc[0]["output_path"]).strip()
    return path or None


def _closure_status(rows: list[dict[str, Any]]) -> str:
    blocking = [row for row in rows if row["blocking"]]
    if not blocking:
        return XG_REPORTING_LAYER_COMPLETE
    ready_count = sum(not row["blocking"] for row in rows if row["check_name"] != "legacy_add_manual_xg_values_non_blocking")
    return XG_REPORTING_LAYER_PARTIAL if ready_count else XG_REPORTING_LAYER_BLOCKED


def _final_recommendation(rows: list[dict[str, Any]], closure_status: str) -> str:
    pack_rows = [row for row in rows if row["check_name"] == "reporting_pack"]
    if pack_rows and pack_rows[0]["recommendation"] == BUILD_XG_REPORTING_PACK_PREVIEW:
        return BUILD_XG_REPORTING_PACK_PREVIEW
    if closure_status == XG_REPORTING_LAYER_COMPLETE:
        return XG_REPORTING_LAYER_COMPLETE_READY_FOR_HUMAN_DIAGNOSTICS
    return FIX_XG_REPORTING_LAYER


def build_markdown(table: pd.DataFrame, closure_status: str, rec: str, manifest_id: str) -> str:
    lines = [
        "# Phase 13.21 xG Reporting Layer Closure Audit",
        "",
        "Phase 13.21 is a closure/diagnostic audit only. xG remains inactive in model logic by design.",
        "",
        "## A. Executive Summary",
        f"- manifest_id: {manifest_id}",
        f"- closure_status: {closure_status}",
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
        "## C. Legacy Audit Semantics",
        "`ADD_MANUAL_XG_VALUES` remains acceptable in legacy data-contract audits while production target CSVs are intentionally not modified in place. The reporting layer uses accepted artifacts and runtime preview files under outputs/.",
        "",
        "## D. Safety Checks",
        "- No xG values inferred or invented.",
        "- No target CSV modified in place.",
        "- No accepted xG artifact modified.",
        "- No raw Understat source CSV modified.",
        "- No production manifest modified.",
        "- No model feature activation.",
        "- No probability, market ranking, recommended-market, betting, staking, ROI, stake sizing, or SUPER_A_TIER logic changed.",
        "",
        "## E. Phase 13.21 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(
    *,
    manifest: str | Path = ROOT / "data" / "templates" / "manual_xg_manifest_template.csv",
    manifest_id: str | None = None,
    window: int = 5,
    preview_dir: str | Path = ROOT / "outputs" / "xg_reporting_preview",
    output_dir: str | Path = ROOT / "outputs" / "diagnostics",
    base_dir: str | Path = ROOT,
    no_build: bool = False,
) -> tuple[pd.DataFrame, str, str]:
    base = Path(base_dir).resolve()
    preview = Path(preview_dir)
    if not preview.is_absolute():
        preview = base / preview
    manifest_path = Path(manifest)
    if not manifest_path.is_absolute():
        manifest_path = base / manifest_path

    pack_summary = _ensure_pack(manifest=manifest_path, manifest_id=manifest_id, window=window, preview_dir=preview, base_dir=base, no_build=no_build)
    rows: list[dict[str, Any]] = []

    manifest_table, _manifest_md, manifest_rec = run_manifest_readiness(manifest=manifest_path, manifest_id=manifest_id, output_dir=output_dir, base_dir=base)
    rows.append(_row("manifest_readiness", manifest_rec, manifest_rec, _first_detail(manifest_table, "readiness_status", "join_coverage_pct"), manifest_rec != MANIFEST_XG_READINESS_READY))

    reporting_table, _reporting_md, reporting_rec = run_reporting_audit(preview=_pack_path(preview, "match_level_reporting_preview"), preview_dir=preview, target=None, output_dir=output_dir, expected_rows=None)
    rows.append(_row("match_level_reporting_preview", reporting_rec, reporting_rec, _first_detail(reporting_table, "rows_reported", "missing_xg_rows"), reporting_rec != XG_REPORTING_PREVIEW_READY))

    team_table, _team_md, team_rec = run_team_audit(preview=_pack_path(preview, "team_xg_reporting_aggregates"), preview_dir=preview, output_dir=output_dir, expected_team_match_rows=None)
    rows.append(_row("team_xg_reporting_aggregates", team_rec, team_rec, _first_detail(team_table, "teams_reported", "matches_used"), team_rec != TEAM_XG_REPORTING_AGGREGATES_READY))

    rolling_table, _rolling_md, rolling_rec = run_rolling_audit(preview=_pack_path(preview, "rolling_xg_form_reporting"), preview_dir=preview, output_dir=output_dir, expected_team_match_rows=None, expected_teams=None)
    rows.append(_row("rolling_xg_form_reporting", rolling_rec, rolling_rec, _first_detail(rolling_table, "teams_reported", "team_match_rows"), rolling_rec != ROLLING_XG_FORM_REPORTING_READY))

    matchup_table, _matchup_md, matchup_rec = run_matchup_audit(preview=_pack_path(preview, "xg_matchup_reporting_preview"), preview_dir=preview, output_dir=output_dir, expected_rows=None)
    rows.append(_row("xg_matchup_reporting_preview", matchup_rec, matchup_rec, _first_detail(matchup_table, "matches_reported", "missing_rolling_context_rows"), matchup_rec != XG_MATCHUP_REPORTING_PREVIEW_READY))

    pack_table, _pack_md, pack_rec = run_pack_audit(preview_dir=preview, output_dir=output_dir, base_dir=base)
    pack_details = _first_detail(pack_table, "reports_found", "reports_ready")
    if not pack_table.empty and "reports_ready" in pack_table.columns:
        pack_summary["reports_ready"] = int(pack_table.iloc[0]["reports_ready"])
    rows.append(_row("reporting_pack", pack_rec, pack_rec, pack_details, pack_rec != XG_REPORTING_PACK_PREVIEW_READY))

    rows.append(_row("legacy_add_manual_xg_values_non_blocking", "ACCEPTABLE_NON_BLOCKING", "LEGACY_ADD_MANUAL_XG_VALUES_ACCEPTABLE", "Production target CSVs intentionally remain unmodified; legacy audits may still request manual xG values.", False))

    closure = _closure_status(rows)
    rec = _final_recommendation(rows, closure)
    table = pd.DataFrame(rows)
    manifest_value = manifest_id or str(pack_summary.get("manifest_id") or (manifest_table.iloc[0]["manifest_id"] if not manifest_table.empty and "manifest_id" in manifest_table.columns else ""))
    markdown = build_markdown(table, closure, rec, manifest_value)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / OUTPUT_CSV, index=False)
    (out / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown, rec


def summarize_closure(table: pd.DataFrame, rec: str) -> dict[str, Any]:
    closure = _closure_status(table.to_dict("records")) if not table.empty else XG_REPORTING_LAYER_BLOCKED
    pack = table[table["check_name"].eq("reporting_pack")] if not table.empty and "check_name" in table.columns else pd.DataFrame()
    reports_ready = 0
    if not pack.empty:
        details = str(pack.iloc[0].get("details", ""))
        for part in details.split(";"):
            if part.strip().startswith("reports_ready="):
                reports_ready = int(float(part.split("=", 1)[1]))
    return {
        "closure_status": closure,
        "reporting_pack_status": pack.iloc[0]["status"] if not pack.empty else "",
        "reports_ready": reports_ready,
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
        output_dir=args.output_dir,
        base_dir=args.base_dir,
        no_build=args.no_build,
    )
    summary = summarize_closure(table, rec)
    for key in ["closure_status", "reporting_pack_status", "reports_ready", "model_integration_status", "recommendation"]:
        print(f"{key}={summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
