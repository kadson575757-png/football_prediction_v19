# -*- coding: utf-8 -*-
"""Audit the one-command real match analysis preview output."""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from run_match_analysis_preview import run_match_analysis_preview  # noqa: E402

REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY = "REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY"
BUILD_REAL_MATCH_ANALYSIS_COMMAND_PREVIEW = "BUILD_REAL_MATCH_ANALYSIS_COMMAND_PREVIEW"
FIX_REAL_MATCH_ANALYSIS_COMMAND_PREVIEW = "FIX_REAL_MATCH_ANALYSIS_COMMAND_PREVIEW"
EXCEL_EXPORT_BLOCKED_MISSING_OPENPYXL = "EXCEL_EXPORT_BLOCKED_MISSING_OPENPYXL"
OUTPUT_CSV = "real_match_analysis_command_preview_summary.csv"
OUTPUT_MD = "real_match_analysis_command_preview_summary.md"
REQUIRED_ARTIFACT_TYPES = {
    "match_context_bundle", "context_human_input", "v19_diagnostic_synthesis",
    "v19_diagnostic_gate_matrix", "human_24_block_report", "export_bundle_manifest",
    "excel_workbook", "command_manifest", "command_summary",
}
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]
FORBIDDEN_TERMS = ["stake size", "return on investment", "super_a", "bet this", " units"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command-manifest", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _as_bool(value: Any) -> bool:
    return value if isinstance(value, bool) else str(value).strip().lower() in {"true", "1", "yes"}


def _openpyxl_available() -> bool:
    try:
        importlib.import_module("openpyxl")
        return True
    except ImportError:
        return False


def _under(path_text: str, base: Path, rel: str) -> bool:
    if not str(path_text).strip():
        return False
    path = Path(path_text)
    if not path.is_absolute():
        path = base / path
    resolved = path.resolve()
    allowed = (base / rel).resolve()
    return resolved == allowed or allowed in resolved.parents


def _protected(path_text: str) -> bool:
    return any(token in str(path_text).replace("\\", "/").lower() for token in PROTECTED)


def audit_manifest(path: Path, *, base_dir: str | Path = ROOT) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    errors: list[str] = []
    manifest = pd.read_csv(path, low_memory=False).iloc[0]
    index_path = Path(str(manifest.get("artifact_index_path", "")))
    index = pd.read_csv(index_path, low_memory=False) if index_path.exists() else pd.DataFrame()
    summary_text_value = str(manifest.get("summary_path", "")).strip()
    summary_path = Path(summary_text_value) if summary_text_value else path.parent / "real_match_analysis_command_summary.md"
    summary_text = summary_path.read_text(encoding="utf-8").lower() if summary_path.exists() else ""
    index_md = index_path.with_suffix(".md")
    index_text = index_md.read_text(encoding="utf-8").lower() if index_md.exists() else ""
    artifact_types = set(index["artifact_type"].astype(str)) if not index.empty and "artifact_type" in index.columns else set()
    paths_safe = True
    if not index.empty and "artifact_path" in index.columns:
        for path_text in index["artifact_path"].astype(str):
            if not _under(path_text, base, "outputs/analysis_preview") or _protected(path_text):
                paths_safe = False
                break
    text = summary_text + " " + index_text
    no_forbidden = not any(term in text for term in FORBIDDEN_TERMS)
    flags_disabled = not any(_as_bool(manifest.get(column, False)) for column in [
        "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled",
        "staking_logic_enabled", "roi_logic_enabled",
    ])
    workbook_exists = _as_bool(manifest.get("workbook_file_exists", False)) if _openpyxl_available() else True
    for ok, label in [
        (str(manifest.get("command_status", "")) == REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY, "COMMAND_NOT_READY"),
        (REQUIRED_ARTIFACT_TYPES.issubset(artifact_types), "ARTIFACT_TYPES_MISSING"),
        (paths_safe, "UNSAFE_ARTIFACT_PATH"),
        (workbook_exists, "WORKBOOK_MISSING"),
        (int(manifest.get("gates_evaluated", 0)) >= 19, "GATES_NOT_READY"),
        (int(manifest.get("sections_rendered", 0)) == 24 and int(manifest.get("required_sections_rendered", 0)) == 24, "SECTIONS_NOT_READY"),
        (int(manifest.get("exported_files_count", 0)) >= 6, "EXPORT_FILES_MISSING"),
        (int(manifest.get("sheets_written", 0)) >= 8 if _openpyxl_available() else True, "SHEETS_NOT_READY"),
        (flags_disabled, "RUNTIME_FLAGS_ENABLED"),
        (no_forbidden, "FORBIDDEN_LANGUAGE_PRESENT"),
    ]:
        if not ok:
            errors.append(label)
    return {
        "command_manifest": str(path),
        "command_status": str(manifest.get("command_status", "")),
        "match_context_bundle_status": str(manifest.get("match_context_bundle_status", "")),
        "context_bridge_status": str(manifest.get("context_bridge_status", "")),
        "v19_diagnostic_synthesis_status": str(manifest.get("v19_diagnostic_synthesis_status", "")),
        "v19_diagnostic_gate_matrix_status": str(manifest.get("v19_diagnostic_gate_matrix_status", "")),
        "human_24_block_report_status": str(manifest.get("human_24_block_report_status", "")),
        "export_bundle_status": str(manifest.get("export_bundle_status", "")),
        "excel_export_status": str(manifest.get("excel_export_status", "")),
        "gates_evaluated": int(manifest.get("gates_evaluated", 0)),
        "sections_rendered": int(manifest.get("sections_rendered", 0)),
        "required_sections_rendered": int(manifest.get("required_sections_rendered", 0)),
        "exported_files_count": int(manifest.get("exported_files_count", 0)),
        "sheets_written": int(manifest.get("sheets_written", 0)),
        "workbook_file_exists": _as_bool(manifest.get("workbook_file_exists", False)),
        "network_calls_enabled": _as_bool(manifest.get("network_calls_enabled", False)),
        "prediction_logic_enabled": _as_bool(manifest.get("prediction_logic_enabled", False)),
        "betting_logic_enabled": _as_bool(manifest.get("betting_logic_enabled", False)),
        "staking_logic_enabled": _as_bool(manifest.get("staking_logic_enabled", False)),
        "roi_logic_enabled": _as_bool(manifest.get("roi_logic_enabled", False)),
        "preview_valid": not errors,
        "blocking_reasons": " | ".join(errors),
    }


def recommendation(table: pd.DataFrame) -> str:
    if not _openpyxl_available():
        return EXCEL_EXPORT_BLOCKED_MISSING_OPENPYXL
    if table.empty:
        return BUILD_REAL_MATCH_ANALYSIS_COMMAND_PREVIEW
    if table["preview_valid"].any():
        return REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY
    return FIX_REAL_MATCH_ANALYSIS_COMMAND_PREVIEW


def run(
    *,
    command_manifest: str | Path | None = None,
    output_dir: str | Path = ROOT / "outputs" / "diagnostics",
    base_dir: str | Path = ROOT,
) -> tuple[pd.DataFrame, str, str]:
    base = Path(base_dir).resolve()
    manifest = Path(command_manifest) if command_manifest else None
    if manifest is None or not manifest.exists():
        summary = run_match_analysis_preview(
            cross_provider_match_key="u-bundesliga-2024-001",
            output_dir=base / "outputs" / "analysis_preview" / "real_match_analysis_command",
            base_dir=base,
        )
        manifest = Path(str(summary.get("manifest_path", "")))
    rows = [audit_manifest(manifest, base_dir=base)] if manifest and manifest.exists() else []
    table = pd.DataFrame(rows)
    rec = recommendation(table)
    markdown = "\n".join([
        "# Phase 25 Real Match Analysis Command Audit",
        "",
        f"- flows audited: {len(table)}",
        f"- valid flows: {int(table['preview_valid'].sum()) if not table.empty else 0}",
        "- one-command output is preview-only",
        "- no production model, probability, market, betting, position sizing, financial-return, or premium tier-label logic is invoked",
        "",
        "## Recommendation",
        rec,
        "",
    ])
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / OUTPUT_CSV, index=False)
    (out / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown, rec


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, _markdown, rec = run(command_manifest=args.command_manifest, output_dir=args.output_dir, base_dir=args.base_dir)
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
