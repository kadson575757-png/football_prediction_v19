# -*- coding: utf-8 -*-
"""Preview-only Excel workbook export for match analysis review bundles."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import importlib

import pandas as pd

MATCH_ANALYSIS_EXCEL_EXPORT_PREVIEW_READY = "MATCH_ANALYSIS_EXCEL_EXPORT_PREVIEW_READY"
EXCEL_EXPORT_BLOCKED_MISSING_OPENPYXL = "EXCEL_EXPORT_BLOCKED_MISSING_OPENPYXL"
EXCEL_EXPORT_BLOCKED_MISSING_EXPORT_BUNDLE = "EXCEL_EXPORT_BLOCKED_MISSING_EXPORT_BUNDLE"
EXCEL_EXPORT_BLOCKED_UNSAFE_PATH = "EXCEL_EXPORT_BLOCKED_UNSAFE_PATH"
EXCEL_EXPORT_NO_MODEL_INTEGRATION_BY_DESIGN = "EXCEL_EXPORT_NO_MODEL_INTEGRATION_BY_DESIGN"
EXCEL_EXPORT_NO_BETTING_INTEGRATION_BY_DESIGN = "EXCEL_EXPORT_NO_BETTING_INTEGRATION_BY_DESIGN"
EXCEL_EXPORT_NO_STAKING_INTEGRATION_BY_DESIGN = "EXCEL_EXPORT_NO_STAKING_INTEGRATION_BY_DESIGN"
EXCEL_EXPORT_NETWORK_DISABLED_BY_DESIGN = "EXCEL_EXPORT_NETWORK_DISABLED_BY_DESIGN"

MANIFEST_COLUMNS = [
    "excel_export_run_id", "export_bundle_dir", "workbook_output_path",
    "sheets_written", "rows_written_total", "workbook_file_exists",
    "excel_export_status", "recommendation", "notes", "network_calls_enabled",
    "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled",
    "roi_logic_enabled",
]
REQUIRED_FILES = {
    "Match Identity": "match_identity.csv",
    "Context Human Input": "context_human_input_review.csv",
    "v19 Diagnostic Synthesis": "v19_diagnostic_synthesis_review.csv",
    "v19 Gate Matrix": "v19_diagnostic_gate_matrix_review.csv",
    "Odds Market Input": "odds_market_movement_input_review.csv",
    "Market Movement Diagnostic": "market_movement_diagnostic_review.csv",
    "Lineups Availability": "lineups_availability_input_review.csv",
    "Availability Diagnostic": "availability_diagnostic_review.csv",
    "Player Impact Form": "player_impact_rolling_form_input_review.csv",
    "Player Form Diagnostic": "player_form_diagnostic_review.csv",
    "24 Block Report Sections": "report_sections_review.csv",
    "Safety Flags": "export_safety_flags.csv",
    "Export Manifest": "match_analysis_export_bundle_manifest.csv",
}
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class MatchAnalysisExcelExportConfig:
    export_bundle_dir: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/match_analysis_excel_export"
    workbook_filename: str = "match_analysis_preview_workbook.xlsx"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class MatchAnalysisExcelExportResult:
    excel_export_run_id: str
    export_bundle_dir: str
    workbook_output_path: str
    manifest_path: str
    summary_path: str
    sheets_written: int
    rows_written_total: int
    workbook_file_exists: bool
    excel_export_status: str
    recommendation: str
    notes: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool


class MatchAnalysisExcelExportRunner:
    def __init__(self, config: MatchAnalysisExcelExportConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> MatchAnalysisExcelExportResult:
        out = _safe_output(self.config.output_dir, self.base)
        if out is None or _unsafe(self.config.export_bundle_dir or ""):
            return self._blocked(EXCEL_EXPORT_BLOCKED_UNSAFE_PATH)
        openpyxl = _load_openpyxl()
        if openpyxl is None:
            return self._blocked(EXCEL_EXPORT_BLOCKED_MISSING_OPENPYXL)
        bundle_dir = _resolve(self.config.export_bundle_dir, self.base) or self.base / "outputs" / "analysis_preview" / "match_analysis_export_bundle"
        if not bundle_dir.exists():
            from scripts.build_match_analysis_export_bundle_preview import build_match_analysis_export_bundle_preview

            summary = build_match_analysis_export_bundle_preview(output_dir=bundle_dir, base_dir=self.base)
            if summary.get("export_bundle_status") != "MATCH_ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY":
                return self._blocked(EXCEL_EXPORT_BLOCKED_MISSING_EXPORT_BUNDLE, bundle_dir=bundle_dir)
        if not all((bundle_dir / filename).exists() for filename in REQUIRED_FILES.values()):
            return self._blocked(EXCEL_EXPORT_BLOCKED_MISSING_EXPORT_BUNDLE, bundle_dir=bundle_dir)

        Workbook = openpyxl.Workbook
        Font = openpyxl.styles.Font
        Alignment = openpyxl.styles.Alignment
        PatternFill = openpyxl.styles.PatternFill
        wb = Workbook()
        ws = wb.active
        ws.title = "README"
        readme_rows = [
            ["Match Analysis Preview Workbook"],
            ["This workbook is for human review of preview artifacts only."],
            ["Production prediction logic is not executed."],
            ["Betting output, position sizing, and financial return tracking are disabled."],
            ["No model, probability, market-tier, recommended-market, betting, staking, or premium tier-label logic is changed."],
        ]
        for row in readme_rows:
            ws.append(row)
        _style_sheet(ws, Font, Alignment, PatternFill)
        rows_total = len(readme_rows)
        sheets_written = 1
        for sheet_name, filename in REQUIRED_FILES.items():
            frame = pd.read_csv(bundle_dir / filename, low_memory=False)
            sheet = wb.create_sheet(sheet_name[:31])
            _write_frame(sheet, frame)
            _style_sheet(sheet, Font, Alignment, PatternFill)
            rows_total += len(frame) + 1
            sheets_written += 1
        out.mkdir(parents=True, exist_ok=True)
        workbook_path = out / self.config.workbook_filename
        manifest_path = out / "match_analysis_excel_export_manifest.csv"
        summary_path = out / "match_analysis_excel_export_summary.md"
        wb.save(workbook_path)
        result = MatchAnalysisExcelExportResult(
            "match_analysis_excel_export_preview", str(bundle_dir.resolve()),
            str(workbook_path.resolve()), str(manifest_path.resolve()),
            str(summary_path.resolve()), sheets_written, rows_total, workbook_path.exists(),
            MATCH_ANALYSIS_EXCEL_EXPORT_PREVIEW_READY, MATCH_ANALYSIS_EXCEL_EXPORT_PREVIEW_READY,
            _notes(), False, False, False, False, False,
        )
        pd.DataFrame([{c: getattr(result, c) for c in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest_path, index=False)
        summary_path.write_text(
            "\n".join([
                "# Match Analysis Excel Export Preview",
                "",
                f"- excel_export_status: {result.excel_export_status}",
                f"- workbook_file_exists: {str(result.workbook_file_exists).lower()}",
                "- preview-only workbook for human review",
                "- no production prediction, betting output, position sizing, or financial return tracking",
                "",
            ]),
            encoding="utf-8",
        )
        return result

    def _blocked(self, status: str, *, bundle_dir: Path | None = None) -> MatchAnalysisExcelExportResult:
        return MatchAnalysisExcelExportResult("match_analysis_excel_export_preview", str(bundle_dir or self.config.export_bundle_dir or ""), "", "", "", 0, 0, False, status, status, _notes(), False, False, False, False, False)


def _write_frame(sheet: object, frame: pd.DataFrame) -> None:
    sheet.append([str(c) for c in frame.columns])
    for _, row in frame.iterrows():
        sheet.append([_cell_value(row.get(c, "")) for c in frame.columns])


def _cell_value(value: object) -> object:
    if pd.isna(value):
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return value
    return str(value)


def _style_sheet(sheet: object, Font: object, Alignment: object, PatternFill: object) -> None:
    sheet.freeze_panes = "A2"
    max_col = max(sheet.max_column, 1)
    max_row = max(sheet.max_row, 1)
    sheet.auto_filter.ref = sheet.dimensions
    header_fill = PatternFill("solid", fgColor="D9EAF7")
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    for column_cells in sheet.columns:
        letter = column_cells[0].column_letter
        max_len = min(max(len(str(cell.value or "")) for cell in column_cells) + 2, 60)
        sheet.column_dimensions[letter].width = max(12, max_len)
    for row in sheet.iter_rows(min_row=1, max_row=max_row, max_col=max_col):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")


def _load_openpyxl() -> object | None:
    try:
        return importlib.import_module("openpyxl")
    except ImportError:
        return None


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "match_analysis_excel_export").resolve()
    return resolved if resolved == allowed or allowed in resolved.parents else None


def _resolve(path: str | Path | None, base: Path) -> Path | None:
    if path is None:
        return None
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _unsafe(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return bool(text) and (text.startswith(("http://", "https://")) or any(token in text for token in PROTECTED))


def _notes() -> str:
    return "; ".join([
        EXCEL_EXPORT_NETWORK_DISABLED_BY_DESIGN,
        EXCEL_EXPORT_NO_MODEL_INTEGRATION_BY_DESIGN,
        EXCEL_EXPORT_NO_BETTING_INTEGRATION_BY_DESIGN,
        EXCEL_EXPORT_NO_STAKING_INTEGRATION_BY_DESIGN,
    ])
