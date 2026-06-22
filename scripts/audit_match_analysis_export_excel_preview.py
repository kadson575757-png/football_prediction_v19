# -*- coding: utf-8 -*-
"""Audit match analysis export bundle and Excel workbook preview."""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_match_analysis_excel_export_preview import build_match_analysis_excel_export_preview  # noqa: E402
from build_match_analysis_export_bundle_preview import build_match_analysis_export_bundle_preview  # noqa: E402

MATCH_ANALYSIS_EXPORT_EXCEL_PREVIEW_READY = "MATCH_ANALYSIS_EXPORT_EXCEL_PREVIEW_READY"
BUILD_MATCH_ANALYSIS_EXPORT_EXCEL_PREVIEW = "BUILD_MATCH_ANALYSIS_EXPORT_EXCEL_PREVIEW"
FIX_MATCH_ANALYSIS_EXPORT_EXCEL_PREVIEW = "FIX_MATCH_ANALYSIS_EXPORT_EXCEL_PREVIEW"
EXCEL_EXPORT_BLOCKED_MISSING_OPENPYXL = "EXCEL_EXPORT_BLOCKED_MISSING_OPENPYXL"
OUTPUT_CSV = "match_analysis_export_excel_preview_summary.csv"
OUTPUT_MD = "match_analysis_export_excel_preview_summary.md"
REQUIRED_SHEETS = [
    "README", "Match Identity", "Context Human Input", "v19 Diagnostic Synthesis",
    "v19 Gate Matrix", "24 Block Report Sections", "Safety Flags", "Export Manifest",
]
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]
FORBIDDEN_TERMS = ["stake size", "return on investment", "super_a", "bet this", " units"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-bundle-manifest", default=None)
    parser.add_argument("--excel-manifest", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _as_bool(value: Any) -> bool:
    return value if isinstance(value, bool) else str(value).strip().lower() in {"true", "1", "yes"}


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


def _openpyxl_available() -> bool:
    try:
        importlib.import_module("openpyxl")
        return True
    except ImportError:
        return False


def audit_pair(export_bundle_manifest: Path, excel_manifest: Path, *, base_dir: str | Path = ROOT) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    errors: list[str] = []
    bundle = pd.read_csv(export_bundle_manifest, low_memory=False).iloc[0]
    excel = pd.read_csv(excel_manifest, low_memory=False).iloc[0]
    workbook_path = str(excel.get("workbook_output_path", ""))
    sheets: list[str] = []
    workbook_text = ""
    if workbook_path and Path(workbook_path).exists() and _openpyxl_available():
        openpyxl = importlib.import_module("openpyxl")
        wb = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
        sheets = list(wb.sheetnames)
        for sheet_name in ["README", "Safety Flags"]:
            ws = wb[sheet_name]
            values = []
            for row in ws.iter_rows(values_only=True):
                values.extend("" if value is None else str(value) for value in row)
            workbook_text += " ".join(values).lower() + " "
        wb.close()
    required_sheets_ok = all(sheet in sheets for sheet in REQUIRED_SHEETS)
    no_forbidden = not any(term in workbook_text for term in FORBIDDEN_TERMS)
    safe_paths = _under(workbook_path, base, "outputs/analysis_preview") and not _protected(workbook_path)
    flags_disabled = not any(_as_bool(excel.get(column, False)) for column in [
        "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled",
        "staking_logic_enabled", "roi_logic_enabled",
    ])
    for ok, label in [
        (str(bundle.get("export_bundle_status", "")) == "MATCH_ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY", "BUNDLE_NOT_READY"),
        (str(excel.get("excel_export_status", "")) == "MATCH_ANALYSIS_EXCEL_EXPORT_PREVIEW_READY", "EXCEL_NOT_READY"),
        (int(bundle.get("exported_files_count", 0)) >= 6, "EXPORT_FILES_MISSING"),
        (int(excel.get("sheets_written", 0)) >= 8, "SHEETS_NOT_WRITTEN"),
        (int(bundle.get("sections_rendered", 0)) == 24 and int(bundle.get("required_sections_rendered", 0)) == 24, "SECTIONS_NOT_READY"),
        (int(bundle.get("gates_evaluated", 0)) >= 19, "GATES_NOT_READY"),
        (bool(excel.get("workbook_file_exists", False)) or str(excel.get("workbook_file_exists", "")).lower() == "true", "WORKBOOK_MISSING"),
        (required_sheets_ok, "REQUIRED_SHEETS_MISSING"),
        (safe_paths, "UNSAFE_WORKBOOK_PATH"),
        (flags_disabled, "RUNTIME_FLAGS_ENABLED"),
        (no_forbidden, "FORBIDDEN_WORKBOOK_LANGUAGE_PRESENT"),
    ]:
        if not ok:
            errors.append(label)
    return {
        "export_bundle_manifest": str(export_bundle_manifest),
        "excel_manifest": str(excel_manifest),
        "export_bundle_status": str(bundle.get("export_bundle_status", "")),
        "excel_export_status": str(excel.get("excel_export_status", "")),
        "exported_files_count": int(bundle.get("exported_files_count", 0)),
        "sheets_written": int(excel.get("sheets_written", 0)),
        "workbook_file_exists": bool(excel.get("workbook_file_exists", False)) or str(excel.get("workbook_file_exists", "")).lower() == "true",
        "gates_evaluated": int(bundle.get("gates_evaluated", 0)),
        "sections_rendered": int(bundle.get("sections_rendered", 0)),
        "required_sections_rendered": int(bundle.get("required_sections_rendered", 0)),
        "network_calls_enabled": _as_bool(excel.get("network_calls_enabled", False)),
        "prediction_logic_enabled": _as_bool(excel.get("prediction_logic_enabled", False)),
        "betting_logic_enabled": _as_bool(excel.get("betting_logic_enabled", False)),
        "staking_logic_enabled": _as_bool(excel.get("staking_logic_enabled", False)),
        "roi_logic_enabled": _as_bool(excel.get("roi_logic_enabled", False)),
        "preview_valid": not errors,
        "blocking_reasons": " | ".join(errors),
    }


def recommendation(table: pd.DataFrame) -> str:
    if not _openpyxl_available():
        return EXCEL_EXPORT_BLOCKED_MISSING_OPENPYXL
    if table.empty:
        return BUILD_MATCH_ANALYSIS_EXPORT_EXCEL_PREVIEW
    if table["preview_valid"].any():
        return MATCH_ANALYSIS_EXPORT_EXCEL_PREVIEW_READY
    return FIX_MATCH_ANALYSIS_EXPORT_EXCEL_PREVIEW


def run(
    *,
    export_bundle_manifest: str | Path | None = None,
    excel_manifest: str | Path | None = None,
    output_dir: str | Path = ROOT / "outputs" / "diagnostics",
    base_dir: str | Path = ROOT,
) -> tuple[pd.DataFrame, str, str]:
    base = Path(base_dir).resolve()
    bundle_manifest = Path(export_bundle_manifest) if export_bundle_manifest else None
    xlsx_manifest = Path(excel_manifest) if excel_manifest else None
    if bundle_manifest is None or xlsx_manifest is None or not bundle_manifest.exists() or not xlsx_manifest.exists():
        bundle = build_match_analysis_export_bundle_preview(cross_provider_match_key="u-bundesliga-2024-001", output_dir=base / "outputs" / "analysis_preview" / "match_analysis_export_bundle", base_dir=base)
        excel = build_match_analysis_excel_export_preview(export_bundle_dir=bundle.get("export_bundle_dir"), output_dir=base / "outputs" / "analysis_preview" / "match_analysis_excel_export", base_dir=base)
        bundle_manifest = Path(str(bundle.get("manifest_path", "")))
        xlsx_manifest = Path(str(excel.get("manifest_path", "")))
    rows = [audit_pair(bundle_manifest, xlsx_manifest, base_dir=base)] if bundle_manifest.exists() and xlsx_manifest.exists() else []
    table = pd.DataFrame(rows)
    rec = recommendation(table)
    markdown = "\n".join([
        "# Phase 24 Match Analysis Export Excel Audit",
        "",
        f"- flows audited: {len(table)}",
        f"- valid flows: {int(table['preview_valid'].sum()) if not table.empty else 0}",
        "- export and workbook are preview-only",
        "- no production model, probability, market, betting, position sizing, financial-return, or SUPER_A_TIER logic is invoked",
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
    table, _markdown, rec = run(export_bundle_manifest=args.export_bundle_manifest, excel_manifest=args.excel_manifest, output_dir=args.output_dir, base_dir=args.base_dir)
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
