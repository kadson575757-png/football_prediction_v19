# -*- coding: utf-8 -*-
"""Audit manifest-backed xG readiness across accepted artifact and preview layers."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_manifest_xg_enrichment_preview import (  # noqa: E402
    MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_INVALID_MANIFEST,
    MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_LOW_COVERAGE,
    MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_MISSING_ARTIFACT,
    MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_UNSAFE_PATH,
    MANIFEST_XG_ENRICHMENT_PREVIEW_READY,
    _is_outputs_path,
    build_manifest_xg_enrichment_preview,
)
from football_prediction_v19.importers.manual_xg_manifest import load_manual_xg_manifest  # noqa: E402

MANIFEST_XG_READY_FOR_REPORTING_PREVIEW = "MANIFEST_XG_READY_FOR_REPORTING_PREVIEW"
MANIFEST_XG_BLOCKED_MISSING_ARTIFACT = "MANIFEST_XG_BLOCKED_MISSING_ARTIFACT"
MANIFEST_XG_BLOCKED_MISSING_TARGET = "MANIFEST_XG_BLOCKED_MISSING_TARGET"
MANIFEST_XG_BLOCKED_LOW_COVERAGE = "MANIFEST_XG_BLOCKED_LOW_COVERAGE"
MANIFEST_XG_BLOCKED_UNSAFE_PATH = "MANIFEST_XG_BLOCKED_UNSAFE_PATH"
MANIFEST_XG_BLOCKED_INVALID_MANIFEST = "MANIFEST_XG_BLOCKED_INVALID_MANIFEST"

XG_MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN = "XG_MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN"

MANIFEST_XG_READINESS_READY = "MANIFEST_XG_READINESS_READY"
FIX_MANIFEST_XG_READINESS = "FIX_MANIFEST_XG_READINESS"
ADD_ACCEPTED_XG_MANIFEST_ENTRY = "ADD_ACCEPTED_XG_MANIFEST_ENTRY"

OUTPUT_CSV = "manifest_xg_readiness_summary.csv"
OUTPUT_MD = "manifest_xg_readiness_summary.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(ROOT / "data" / "templates" / "manual_xg_manifest_template.csv"))
    parser.add_argument("--manifest-id", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _repo_relative(path: str | Path, base_dir: Path) -> str:
    text = str(path).strip()
    if not text:
        raise ValueError("EMPTY_PATH")
    raw = Path(text)
    if raw.is_absolute():
        raise ValueError("MANIFEST_PATH_MUST_BE_REPO_RELATIVE")
    return raw.as_posix()


def _accepted_production_entries(manifest: Path) -> list[Any]:
    return [
        entry for entry in load_manual_xg_manifest(manifest)
        if entry.data_role == "PRODUCTION"
        and entry.source_type == "MANUAL_XG_CSV"
        and not entry.is_demo
        and str(entry.xg_file_path).strip()
        and str(entry.target_file_path).strip()
    ]


def _readiness_from_enrichment(status: str, blocking: str) -> str:
    if status == MANIFEST_XG_ENRICHMENT_PREVIEW_READY:
        return MANIFEST_XG_READY_FOR_REPORTING_PREVIEW
    if status == MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_MISSING_ARTIFACT:
        return MANIFEST_XG_BLOCKED_MISSING_ARTIFACT
    if status == MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_LOW_COVERAGE:
        return MANIFEST_XG_BLOCKED_LOW_COVERAGE
    if status == MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_UNSAFE_PATH:
        return MANIFEST_XG_BLOCKED_UNSAFE_PATH
    if "TARGET_FILE_NOT_FOUND" in str(blocking):
        return MANIFEST_XG_BLOCKED_MISSING_TARGET
    if status == MANIFEST_XG_ENRICHMENT_PREVIEW_BLOCKED_INVALID_MANIFEST:
        return MANIFEST_XG_BLOCKED_INVALID_MANIFEST
    return MANIFEST_XG_BLOCKED_INVALID_MANIFEST


def _preflight(entry: Any, base_dir: Path) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    try:
        xg_rel = _repo_relative(entry.xg_file_path, base_dir)
        target_rel = _repo_relative(entry.target_file_path, base_dir)
    except ValueError as exc:
        xg_rel = str(entry.xg_file_path)
        target_rel = str(entry.target_file_path)
        errors.append(str(exc))
    artifact_exists = bool(not errors and (base_dir / xg_rel).exists())
    target_exists = bool(not errors and (base_dir / target_rel).exists())
    if not errors:
        if _is_outputs_path(xg_rel) or _is_outputs_path(target_rel):
            errors.append("OUTPUTS_PATH_NOT_ALLOWED")
        if not xg_rel.startswith("data/trusted_xg_sources/accepted/"):
            errors.append("XG_PATH_NOT_UNDER_ACCEPTED_TRUSTED_SOURCES")
        if not artifact_exists:
            errors.append("ACCEPTED_ARTIFACT_NOT_FOUND")
        if not target_exists:
            errors.append("TARGET_FILE_NOT_FOUND")
    if entry.expected_rows is None:
        errors.append("EXPECTED_ROWS_MISSING")
    if entry.min_join_coverage_pct is None:
        errors.append("MIN_JOIN_COVERAGE_MISSING")
    return {
        "xg_file_path": xg_rel,
        "target_file_path": target_rel,
        "artifact_exists": artifact_exists,
        "target_exists": target_exists,
        "preflight_errors": errors,
    }, errors


def audit_entry(entry: Any, manifest: Path, base_dir: Path) -> dict[str, Any]:
    preflight, errors = _preflight(entry, base_dir)
    summary = build_manifest_xg_enrichment_preview(
        manifest=manifest,
        manifest_id=entry.manifest_id,
        output_dir=base_dir / "outputs" / "xg_enrichment_preview",
        write_preview=False,
        base_dir=base_dir,
    )
    readiness = _readiness_from_enrichment(summary["enrichment_status"], summary.get("blocking_reasons", ""))
    if errors and readiness == MANIFEST_XG_READY_FOR_REPORTING_PREVIEW:
        readiness = MANIFEST_XG_BLOCKED_INVALID_MANIFEST
    recommendation = MANIFEST_XG_READINESS_READY if readiness == MANIFEST_XG_READY_FOR_REPORTING_PREVIEW else FIX_MANIFEST_XG_READINESS
    return {
        "manifest_id": entry.manifest_id,
        "league": entry.league,
        "season": entry.season,
        "xg_file_path": preflight["xg_file_path"],
        "target_file_path": preflight["target_file_path"],
        "artifact_exists": preflight["artifact_exists"],
        "target_exists": preflight["target_exists"],
        "rows_target": summary["rows_target"],
        "rows_enriched": summary["rows_enriched"],
        "rows_missing_xg": summary["rows_missing_xg"],
        "join_coverage_pct": summary["join_coverage_pct"],
        "enrichment_status": summary["enrichment_status"],
        "readiness_status": readiness,
        "model_integration_status": XG_MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN,
        "recommendation": recommendation,
        "blocking_reasons": " | ".join(sorted(set(errors + [summary.get("blocking_reasons", "")]))).strip(" |"),
    }


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return ADD_ACCEPTED_XG_MANIFEST_ENTRY
    if table["readiness_status"].eq(MANIFEST_XG_READY_FOR_REPORTING_PREVIEW).all():
        return MANIFEST_XG_READINESS_READY
    return FIX_MANIFEST_XG_READINESS


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    lines = [
        "# Phase 13.15 Manifest-backed xG Readiness Audit",
        "",
        "Phase 13.15 is diagnostic/foundation only. xG can be used for reporting/diagnostic previews, but model integration is not active by design.",
        "",
        "## A. Executive Summary",
        f"- accepted production entries audited: {len(table)}",
        f"- readiness-ready entries: {int(table['readiness_status'].eq(MANIFEST_XG_READY_FOR_REPORTING_PREVIEW).sum()) if not table.empty else 0}",
        f"- model integration status: {XG_MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN}",
        "",
        "## B. Readiness Rows",
    ]
    if table.empty:
        lines += ["No accepted production manifest entries found.", ""]
    else:
        cols = [
            "manifest_id",
            "league",
            "season",
            "rows_target",
            "rows_enriched",
            "rows_missing_xg",
            "join_coverage_pct",
            "readiness_status",
            "model_integration_status",
            "recommendation",
        ]
        lines += ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
        for _, row in table[cols].iterrows():
            lines.append("| " + " | ".join(str(row[col]).replace("|", ";") for col in cols) + " |")
        lines.append("")
    lines += [
        "## C. Audit Semantics",
        "`audit_xg_enrichment_contracts.py` and `audit_data_contracts.py` may still return `ADD_MANUAL_XG_VALUES` because they audit whether production target CSVs themselves contain xG values. This readiness audit instead validates the accepted-artifact -> manifest -> preview chain without modifying targets.",
        "",
        "## D. Safety Checks",
        "- No xG values inferred or invented.",
        "- No target CSV modified in place.",
        "- No accepted artifact modified.",
        "- No raw Understat source CSV modified.",
        "- No production manifest modified.",
        "- No model, probability, market-tier, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "",
        "## E. Phase 13.15 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(
    *,
    manifest: str | Path = ROOT / "data" / "templates" / "manual_xg_manifest_template.csv",
    manifest_id: str | None = None,
    output_dir: str | Path = ROOT / "outputs" / "diagnostics",
    base_dir: str | Path = ROOT,
) -> tuple[pd.DataFrame, str, str]:
    base = Path(base_dir).resolve()
    manifest_path = Path(manifest)
    if not manifest_path.is_absolute():
        manifest_path = base / manifest_path
    entries = _accepted_production_entries(manifest_path)
    if manifest_id:
        entries = [entry for entry in entries if entry.manifest_id == manifest_id]
    rows = [audit_entry(entry, manifest_path, base) for entry in entries]
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
        manifest=args.manifest,
        manifest_id=args.manifest_id,
        output_dir=args.output_dir,
        base_dir=args.base_dir,
    )
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
