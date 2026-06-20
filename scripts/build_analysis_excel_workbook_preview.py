# -*- coding: utf-8 -*-
"""Build an Excel workbook preview from the Phase 14.1 analysis export bundle."""
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

from build_analysis_export_bundle_preview import (  # noqa: E402
    ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY,
    build_analysis_export_bundle_preview,
)
from football_prediction_v19.importers.manual_xg_manifest import load_manual_xg_manifest  # noqa: E402

ANALYSIS_EXCEL_WORKBOOK_PREVIEW_READY = "ANALYSIS_EXCEL_WORKBOOK_PREVIEW_READY"
ANALYSIS_EXCEL_WORKBOOK_PREVIEW_BLOCKED_EXPORT_BUNDLE_FAILED = "ANALYSIS_EXCEL_WORKBOOK_PREVIEW_BLOCKED_EXPORT_BUNDLE_FAILED"
ANALYSIS_EXCEL_WORKBOOK_PREVIEW_BLOCKED_UNSAFE_PATH = "ANALYSIS_EXCEL_WORKBOOK_PREVIEW_BLOCKED_UNSAFE_PATH"
ANALYSIS_EXCEL_WORKBOOK_PREVIEW_BLOCKED_INVALID_MANIFEST = "ANALYSIS_EXCEL_WORKBOOK_PREVIEW_BLOCKED_INVALID_MANIFEST"
ANALYSIS_EXCEL_WORKBOOK_PREVIEW_BLOCKED_MISSING_DEPENDENCY = "ANALYSIS_EXCEL_WORKBOOK_PREVIEW_BLOCKED_MISSING_DEPENDENCY"

XG_MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN = "XG_MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN"

OUTPUT_DIR = ROOT / "outputs" / "analysis_export_preview"
WORKBOOK_NAME = "analysis_export_workbook_preview.xlsx"

SHEET_EXPORTS = {
    "Bundle_Index": "analysis_export_bundle_index.csv",
    "Match_Level": "match_level_xg_reporting_preview.csv",
    "Team_Aggregates": "team_xg_reporting_aggregates.csv",
    "Rolling_Form": "rolling_xg_form_reporting.csv",
    "Matchup_Preview": "xg_matchup_reporting_preview.csv",
    "Reporting_Pack": "xg_reporting_pack_index.csv",
    "Closure_Summary": "xg_reporting_layer_closure_summary.csv",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(ROOT / "data" / "templates" / "manual_xg_manifest_template.csv"))
    parser.add_argument("--manifest-id", default="trusted_xg_understat_bundesliga_2024_manual_xg")
    parser.add_argument("--window", type=int, default=5)
    parser.add_argument("--export-bundle-dir", default=None)
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--write-preview", action="store_true")
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _safe_output_dir(output_dir: str | Path, base_dir: Path) -> Path:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base_dir / out
    resolved = out.resolve()
    allowed = (base_dir / "outputs" / "analysis_export_preview").resolve()
    if resolved != allowed and allowed not in resolved.parents:
        raise ValueError("EXCEL_OUTPUT_DIR_MUST_BE_UNDER_OUTPUTS_ANALYSIS_EXPORT_PREVIEW")
    return resolved


def _entry(manifest: Path, manifest_id: str | None) -> Any | None:
    entries = [
        entry for entry in load_manual_xg_manifest(manifest)
        if entry.data_role == "PRODUCTION"
        and entry.source_type == "MANUAL_XG_CSV"
        and not entry.is_demo
        and str(entry.xg_file_path).strip()
        and str(entry.target_file_path).strip()
    ]
    if manifest_id:
        entries = [entry for entry in entries if entry.manifest_id == manifest_id]
    return entries[0] if entries else None


def _blocked(status: str, reason: str, *, manifest_id: str = "") -> dict[str, Any]:
    return {
        "excel_workbook_status": status,
        "manifest_id": manifest_id,
        "sheets_written": 0,
        "workbook_path": "",
        "recommendation": status,
        "blocking_reasons": reason,
    }


def _write_df(ws: Any, df: pd.DataFrame) -> None:
    ws.append(list(df.columns))
    for row in df.itertuples(index=False, name=None):
        ws.append(list(row))


def _autosize(ws: Any) -> None:
    for column in ws.columns:
        width = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column)
        ws.column_dimensions[column[0].column_letter].width = min(max(width + 2, 12), 60)


def _bundle_dir_from_arg(export_bundle_dir: str | Path | None, out_root: Path, manifest_id: str) -> Path:
    if export_bundle_dir:
        path = Path(export_bundle_dir)
        if not path.is_absolute():
            path = out_root.parent.parent / path
        return path.resolve()
    return (out_root / manifest_id).resolve()


def build_analysis_excel_workbook_preview(
    *,
    manifest: str | Path = ROOT / "data" / "templates" / "manual_xg_manifest_template.csv",
    manifest_id: str | None = "trusted_xg_understat_bundesliga_2024_manual_xg",
    window: int = 5,
    export_bundle_dir: str | Path | None = None,
    output_dir: str | Path = OUTPUT_DIR,
    write_preview: bool = False,
    base_dir: str | Path = ROOT,
) -> dict[str, Any]:
    try:
        from openpyxl import Workbook
    except Exception as exc:  # pragma: no cover - dependency presence varies by env
        return _blocked(ANALYSIS_EXCEL_WORKBOOK_PREVIEW_BLOCKED_MISSING_DEPENDENCY, str(exc), manifest_id=manifest_id or "")

    base = Path(base_dir).resolve()
    try:
        out_root = _safe_output_dir(output_dir, base)
    except ValueError as exc:
        return _blocked(ANALYSIS_EXCEL_WORKBOOK_PREVIEW_BLOCKED_UNSAFE_PATH, str(exc), manifest_id=manifest_id or "")
    manifest_path = Path(manifest)
    if not manifest_path.is_absolute():
        manifest_path = base / manifest_path
    try:
        entry = _entry(manifest_path, manifest_id)
    except Exception as exc:
        return _blocked(ANALYSIS_EXCEL_WORKBOOK_PREVIEW_BLOCKED_INVALID_MANIFEST, str(exc), manifest_id=manifest_id or "")
    if entry is None:
        return _blocked(ANALYSIS_EXCEL_WORKBOOK_PREVIEW_BLOCKED_INVALID_MANIFEST, "NO_ACCEPTED_PRODUCTION_MANIFEST_ENTRY", manifest_id=manifest_id or "")

    bundle = build_analysis_export_bundle_preview(
        manifest=manifest_path,
        manifest_id=entry.manifest_id,
        window=window,
        output_dir=out_root,
        write_preview=True,
        base_dir=base,
    )
    if bundle["export_bundle_status"] != ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY:
        return _blocked(ANALYSIS_EXCEL_WORKBOOK_PREVIEW_BLOCKED_EXPORT_BUNDLE_FAILED, str(bundle.get("blocking_reasons", "")), manifest_id=entry.manifest_id)

    bundle_dir = _bundle_dir_from_arg(export_bundle_dir, out_root, entry.manifest_id)
    allowed = out_root.resolve()
    if allowed not in bundle_dir.parents:
        return _blocked(ANALYSIS_EXCEL_WORKBOOK_PREVIEW_BLOCKED_UNSAFE_PATH, "WORKBOOK_BUNDLE_DIR_OUTSIDE_OUTPUT_DIR", manifest_id=entry.manifest_id)

    workbook_path = (bundle_dir / WORKBOOK_NAME).resolve()
    if allowed not in workbook_path.parents:
        return _blocked(ANALYSIS_EXCEL_WORKBOOK_PREVIEW_BLOCKED_UNSAFE_PATH, "WORKBOOK_PATH_OUTSIDE_OUTPUT_DIR", manifest_id=entry.manifest_id)

    sheets_written = 0
    if write_preview:
        wb = Workbook()
        readme = wb.active
        readme.title = "README"
        readme.append(["field", "value"])
        for field, value in [
            ("manifest_id", entry.manifest_id),
            ("league", entry.league),
            ("season", entry.season),
            ("export_status", bundle["export_bundle_status"]),
            ("model_integration_status", XG_MODEL_INTEGRATION_NOT_ACTIVE_BY_DESIGN),
            ("safety_note", "xG is not active in model logic; workbook is reporting/export preview only."),
        ]:
            readme.append([field, value])
        _autosize(readme)
        sheets_written += 1

        for sheet_name, csv_name in SHEET_EXPORTS.items():
            csv_path = bundle_dir / csv_name
            if not csv_path.exists():
                if sheet_name == "Closure_Summary":
                    continue
                return _blocked(ANALYSIS_EXCEL_WORKBOOK_PREVIEW_BLOCKED_EXPORT_BUNDLE_FAILED, f"MISSING_EXPORT_CSV:{csv_name}", manifest_id=entry.manifest_id)
            ws = wb.create_sheet(sheet_name)
            _write_df(ws, pd.read_csv(csv_path, low_memory=False))
            _autosize(ws)
            sheets_written += 1
        workbook_path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(workbook_path)
    else:
        sheets_written = 1 + sum((bundle_dir / csv).exists() for csv in SHEET_EXPORTS.values())

    return {
        "excel_workbook_status": ANALYSIS_EXCEL_WORKBOOK_PREVIEW_READY,
        "manifest_id": entry.manifest_id,
        "sheets_written": int(sheets_written),
        "workbook_path": str(workbook_path) if write_preview else "",
        "recommendation": ANALYSIS_EXCEL_WORKBOOK_PREVIEW_READY,
        "blocking_reasons": "",
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_analysis_excel_workbook_preview(
        manifest=args.manifest,
        manifest_id=args.manifest_id,
        window=args.window,
        export_bundle_dir=args.export_bundle_dir,
        output_dir=args.output_dir,
        write_preview=args.write_preview,
        base_dir=args.base_dir,
    )
    for key in ["excel_workbook_status", "manifest_id", "sheets_written", "workbook_path", "recommendation"]:
        print(f"{key}={summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
