# -*- coding: utf-8 -*-
"""Manual xG production manifest and acceptance register helpers.

Diagnostic/foundation only. Manifest evaluation never modifies the manifest,
xG source files, target files, or model behavior.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from football_prediction_v19.importers.manual_xg_acceptance import (
    MANUAL_XG_ACCEPTED,
    MANUAL_XG_ACCEPTED_WITH_WARNINGS,
    run_manual_xg_acceptance_gate,
)

ALLOWED_SOURCE_TYPES = {"MANUAL_XG_CSV", "DEMO_ONLY", "TEMPLATE_ONLY"}
ALLOWED_DATA_ROLES = {"PRODUCTION", "DEMO", "TEMPLATE"}
REQUIRED_COLUMNS = [
    "manifest_id",
    "xg_file_path",
    "target_file_path",
    "league",
    "season",
    "source_type",
    "data_role",
    "is_demo",
    "expected_rows",
    "min_join_coverage_pct",
    "notes",
]


@dataclass(frozen=True)
class ManualXGManifestEntry:
    manifest_id: str
    xg_file_path: str
    target_file_path: str
    league: str
    season: str
    source_type: str
    data_role: str
    is_demo: bool
    expected_rows: int | None
    min_join_coverage_pct: float
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ManualXGManifestValidationResult:
    manifest_path: str
    entries_total: int
    entries_valid: int
    entries_invalid: int
    demo_entries: int
    production_entries: int
    accepted_production_entries: int
    rejected_production_entries: int
    recommendation: str
    warning_notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _parse_bool(value: Any) -> bool | None:
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def _parse_int(value: Any) -> int | None:
    if pd.isna(value) or str(value).strip() == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _parse_float(value: Any, default: float = 95.0) -> float:
    if pd.isna(value) or str(value).strip() == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _resolve(path: str, base_dir: str | Path | None) -> Path:
    raw = Path(str(path))
    if raw.is_absolute():
        return raw
    return (Path(base_dir or ".") / raw).resolve()


def load_manual_xg_manifest(path: str | Path) -> list[ManualXGManifestEntry]:
    table = pd.read_csv(path, keep_default_na=False)
    missing = [col for col in REQUIRED_COLUMNS if col not in table.columns]
    if missing:
        raise ValueError("manifest missing required columns: " + ", ".join(missing))
    entries: list[ManualXGManifestEntry] = []
    for _, row in table.iterrows():
        is_demo = _parse_bool(row["is_demo"])
        entries.append(ManualXGManifestEntry(
            manifest_id=str(row["manifest_id"]).strip(),
            xg_file_path=str(row["xg_file_path"]).strip(),
            target_file_path=str(row["target_file_path"]).strip(),
            league=str(row["league"]).strip(),
            season=str(row["season"]).strip(),
            source_type=str(row["source_type"]).strip(),
            data_role=str(row["data_role"]).strip(),
            is_demo=bool(is_demo) if is_demo is not None else False,
            expected_rows=_parse_int(row["expected_rows"]),
            min_join_coverage_pct=_parse_float(row["min_join_coverage_pct"]),
            notes=str(row["notes"]).strip(),
        ))
    return entries


def validate_manual_xg_manifest_entry(entry: ManualXGManifestEntry, base_dir: str | Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not entry.manifest_id:
        errors.append("MISSING_MANIFEST_ID")
    if entry.source_type not in ALLOWED_SOURCE_TYPES:
        errors.append("INVALID_SOURCE_TYPE")
    if entry.data_role not in ALLOWED_DATA_ROLES:
        errors.append("INVALID_DATA_ROLE")
    is_production = entry.data_role == "PRODUCTION"
    if is_production and entry.is_demo:
        errors.append("PRODUCTION_ENTRY_MARKED_DEMO")
    if entry.is_demo and is_production:
        errors.append("DEMO_ENTRY_CANNOT_BE_PRODUCTION")
    if is_production:
        if not entry.xg_file_path:
            errors.append("MISSING_XG_FILE_PATH")
        if not entry.target_file_path:
            errors.append("MISSING_TARGET_FILE_PATH")
    if entry.xg_file_path and not _resolve(entry.xg_file_path, base_dir).exists():
        errors.append("XG_FILE_NOT_FOUND")
    if entry.target_file_path and not _resolve(entry.target_file_path, base_dir).exists():
        errors.append("TARGET_FILE_NOT_FOUND")
    if entry.is_demo:
        warnings.append("DEMO_ENTRY_NEVER_COUNTS_AS_PRODUCTION")
    if entry.data_role == "TEMPLATE":
        warnings.append("TEMPLATE_ENTRY_NEVER_COUNTS_AS_PRODUCTION")
    return {
        **entry.to_dict(),
        "entry_valid": not errors,
        "is_production_entry": is_production and not entry.is_demo,
        "entry_errors": errors,
        "entry_warnings": warnings,
        "acceptance_label": "",
        "rows_valid": 0,
        "rows_invalid": 0,
        "rows_join_matched": 0,
        "join_coverage_pct": 0.0,
        "preview_output_path": "",
        "production_accepted": False,
    }


def _recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return "INCONCLUSIVE_NO_MANIFEST"
    if table["production_accepted"].any():
        return "READY_FOR_MANUAL_XG_ENRICHMENT_PIPELINE"
    production = table[table["is_production_entry"] == True]
    if not production.empty:
        return "FIX_MANIFEST_ENTRIES"
    if table["data_role"].isin(["DEMO", "TEMPLATE"]).all():
        return "ADD_PRODUCTION_MANUAL_XG_FILE"
    return "INCONCLUSIVE_NO_MANIFEST"


def validate_manual_xg_manifest(path: str | Path, base_dir: str | Path | None = None) -> ManualXGManifestValidationResult:
    rows = [validate_manual_xg_manifest_entry(entry, base_dir=base_dir) for entry in load_manual_xg_manifest(path)]
    table = pd.DataFrame(rows)
    rec = _recommendation(table)
    return ManualXGManifestValidationResult(
        manifest_path=str(path),
        entries_total=len(table),
        entries_valid=int(table["entry_valid"].sum()) if not table.empty else 0,
        entries_invalid=int((~table["entry_valid"]).sum()) if not table.empty else 0,
        demo_entries=int(table["is_demo"].sum()) if not table.empty else 0,
        production_entries=int(table["is_production_entry"].sum()) if not table.empty else 0,
        accepted_production_entries=0,
        rejected_production_entries=int(len(table[table["is_production_entry"] == True])) if not table.empty else 0,
        recommendation=rec,
        warning_notes=[],
    )


def evaluate_manifest_acceptance(
    path: str | Path,
    base_dir: str | Path | None = None,
    output_dir: str | Path = "outputs/xg_acceptance_preview",
    *,
    include_demo: bool = False,
) -> tuple[pd.DataFrame, ManualXGManifestValidationResult]:
    base = Path(base_dir or Path(path).resolve().parents[2]).resolve()
    rows: list[dict[str, Any]] = []
    for entry in load_manual_xg_manifest(path):
        row = validate_manual_xg_manifest_entry(entry, base_dir=base)
        should_evaluate = row["entry_valid"] and (row["is_production_entry"] or (include_demo and entry.is_demo))
        if should_evaluate and entry.xg_file_path and entry.target_file_path:
            result = run_manual_xg_acceptance_gate(
                _resolve(entry.xg_file_path, base),
                target_path=_resolve(entry.target_file_path, base),
                output_dir=output_dir,
                min_join_coverage=entry.min_join_coverage_pct,
                write_preview=False,
            )
            row.update({
                "acceptance_label": result.acceptance_label,
                "rows_valid": result.rows_valid,
                "rows_invalid": result.rows_invalid,
                "rows_join_matched": result.rows_join_matched,
                "join_coverage_pct": result.join_coverage_pct,
                "preview_output_path": result.preview_output_path,
            })
            row["production_accepted"] = bool(
                row["is_production_entry"]
                and result.acceptance_label in {MANUAL_XG_ACCEPTED, MANUAL_XG_ACCEPTED_WITH_WARNINGS}
            )
            if entry.expected_rows is not None and result.rows_source != entry.expected_rows:
                row["entry_warnings"].append("EXPECTED_ROWS_MISMATCH")
        row["entry_errors"] = " | ".join(row["entry_errors"])
        row["entry_warnings"] = " | ".join(row["entry_warnings"])
        rows.append(row)
    table = pd.DataFrame(rows)
    rec = _recommendation(table)
    summary = ManualXGManifestValidationResult(
        manifest_path=str(path),
        entries_total=len(table),
        entries_valid=int(table["entry_valid"].sum()) if not table.empty else 0,
        entries_invalid=int((~table["entry_valid"]).sum()) if not table.empty else 0,
        demo_entries=int(table["is_demo"].sum()) if not table.empty else 0,
        production_entries=int(table["is_production_entry"].sum()) if not table.empty else 0,
        accepted_production_entries=int(table["production_accepted"].sum()) if not table.empty else 0,
        rejected_production_entries=int(len(table[(table["is_production_entry"] == True) & (table["production_accepted"] == False)])) if not table.empty else 0,
        recommendation=rec,
        warning_notes=[],
    )
    return table, summary


def write_manifest_acceptance_register(results: pd.DataFrame, output_dir: str | Path = "outputs/diagnostics") -> Path:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root / "manual_xg_manifest_acceptance_register.csv"
    results.to_csv(output, index=False)
    return output
