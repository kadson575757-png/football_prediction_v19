# -*- coding: utf-8 -*-
"""File-based importer dry-run preview.

This module reads local CSV files only and validates them against the Phase 15
canonical importer schema contracts. It does not fetch provider data, infer
missing values, or write outside the importer preview output directory.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from football_prediction_v19.importers.adapter_interface import (
    BaseImporterAdapter,
    ImporterAdapterConfig,
    ImporterRunContext,
)

FILE_BASED_IMPORTER_DRY_RUN_READY = "FILE_BASED_IMPORTER_DRY_RUN_READY"
FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_MISSING_FILE = "FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_MISSING_FILE"
FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_MISSING_REQUIRED_COLUMNS = "FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_MISSING_REQUIRED_COLUMNS"
FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_INVALID_CONTRACT = "FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_INVALID_CONTRACT"
FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_UNSAFE_PATH = "FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_UNSAFE_PATH"
FILE_BASED_IMPORTER_NETWORK_DISABLED_BY_DESIGN = "FILE_BASED_IMPORTER_NETWORK_DISABLED_BY_DESIGN"


@dataclass(frozen=True)
class FileBasedImporterConfig:
    source_id: str = "file_csv"
    contract_id: str = "canonical_match"
    input_path: str | Path | None = None
    contracts_path: str | Path | None = None
    output_dir: str | Path = "outputs/importer_preview"
    write_preview: bool = False
    base_dir: str | Path = "."


@dataclass(frozen=True)
class FileBasedImporterResult:
    source_id: str
    contract_id: str
    input_path: str
    output_path: str
    rows_input: int
    rows_normalized: int
    missing_required_columns: str
    network_calls_enabled: bool
    dry_run_status: str
    recommendation: str
    notes: str


class FileBasedImporterAdapter(BaseImporterAdapter):
    """Dry-run adapter for local CSV importer validation."""

    def __init__(self, config: FileBasedImporterConfig) -> None:
        self.file_config = config
        super().__init__(
            ImporterAdapterConfig(
                source_id=config.source_id,
                provider_name="Local CSV",
                supported_contracts=(config.contract_id,),
                network_enabled=False,
            )
        )

    def fetch_raw(self, context: ImporterRunContext) -> Any:
        raise NotImplementedError(FILE_BASED_IMPORTER_NETWORK_DISABLED_BY_DESIGN)

    def normalize(self, raw: Any, context: ImporterRunContext) -> Any:
        raise NotImplementedError(FILE_BASED_IMPORTER_NETWORK_DISABLED_BY_DESIGN)

    def run_dry_run(self) -> tuple[FileBasedImporterResult, pd.DataFrame]:
        cfg = self.file_config
        base = Path(cfg.base_dir).resolve()
        out_dir = _safe_output_dir(cfg.output_dir, base)
        if out_dir is None:
            return _result(cfg, FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_UNSAFE_PATH, "OUTPUT_DIR_MUST_BE_UNDER_OUTPUTS_IMPORTER_PREVIEW"), pd.DataFrame()

        input_path = Path(cfg.input_path) if cfg.input_path is not None else None
        if input_path is None:
            return _result(cfg, FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_MISSING_FILE, "INPUT_PATH_REQUIRED"), pd.DataFrame()
        if not input_path.is_absolute():
            input_path = base / input_path
        if not input_path.exists():
            return _result(cfg, FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_MISSING_FILE, "INPUT_FILE_NOT_FOUND"), pd.DataFrame()

        contracts_path = Path(cfg.contracts_path) if cfg.contracts_path is not None else None
        if contracts_path is None:
            return _result(cfg, FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_INVALID_CONTRACT, "CONTRACTS_PATH_REQUIRED"), pd.DataFrame()
        if not contracts_path.is_absolute():
            contracts_path = base / contracts_path
        if not contracts_path.exists():
            return _result(cfg, FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_INVALID_CONTRACT, "CONTRACTS_FILE_NOT_FOUND"), pd.DataFrame()

        try:
            contracts = pd.read_csv(contracts_path, low_memory=False)
        except Exception as exc:
            return _result(cfg, FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_INVALID_CONTRACT, f"CONTRACTS_READ_FAILED:{exc}"), pd.DataFrame()
        required = required_columns_for_contract(contracts, cfg.contract_id)
        if not required:
            return _result(cfg, FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_INVALID_CONTRACT, "CONTRACT_NOT_FOUND_OR_NO_REQUIRED_COLUMNS"), pd.DataFrame()

        try:
            raw = pd.read_csv(input_path, low_memory=False)
        except Exception as exc:
            return _result(cfg, FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_MISSING_FILE, f"INPUT_READ_FAILED:{exc}", input_path=input_path), pd.DataFrame()
        missing = [column for column in required if column not in raw.columns]
        if missing:
            return _result(
                cfg,
                FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_MISSING_REQUIRED_COLUMNS,
                "MISSING_REQUIRED_COLUMNS",
                input_path=input_path,
                rows_input=len(raw),
                missing_required_columns=" | ".join(missing),
            ), pd.DataFrame()

        contract_fields = contract_columns(contracts, cfg.contract_id)
        normalized = raw[[column for column in contract_fields if column in raw.columns]].copy()
        output_path = ""
        if cfg.write_preview:
            normalized_dir = out_dir / "normalized"
            normalized_dir.mkdir(parents=True, exist_ok=True)
            candidate = (normalized_dir / f"{cfg.contract_id}_preview.csv").resolve()
            if not _is_under(candidate, out_dir):
                return _result(cfg, FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_UNSAFE_PATH, "NORMALIZED_OUTPUT_OUTSIDE_PREVIEW_DIR"), pd.DataFrame()
            normalized.to_csv(candidate, index=False)
            output_path = str(candidate)

        return FileBasedImporterResult(
            source_id=cfg.source_id,
            contract_id=cfg.contract_id,
            input_path=str(input_path.resolve()),
            output_path=output_path,
            rows_input=int(len(raw)),
            rows_normalized=int(len(normalized)),
            missing_required_columns="",
            network_calls_enabled=False,
            dry_run_status=FILE_BASED_IMPORTER_DRY_RUN_READY,
            recommendation=FILE_BASED_IMPORTER_DRY_RUN_READY,
            notes=FILE_BASED_IMPORTER_NETWORK_DISABLED_BY_DESIGN,
        ), normalized


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def contract_columns(contracts: pd.DataFrame, contract_id: str) -> list[str]:
    if "contract_id" not in contracts.columns or "field_name" not in contracts.columns:
        return []
    subset = contracts[contracts["contract_id"].astype(str).eq(str(contract_id))]
    return [str(value) for value in subset["field_name"].dropna().tolist()]


def required_columns_for_contract(contracts: pd.DataFrame, contract_id: str) -> list[str]:
    if "required" not in contracts.columns:
        return []
    subset = contracts[contracts["contract_id"].astype(str).eq(str(contract_id))]
    subset = subset[subset["required"].map(_as_bool)]
    return [str(value) for value in subset["field_name"].dropna().tolist()]


def _safe_output_dir(output_dir: str | Path, base_dir: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base_dir / out
    resolved = out.resolve()
    allowed = (base_dir / "outputs" / "importer_preview").resolve()
    if resolved == allowed or allowed in resolved.parents:
        return resolved
    return None


def _is_under(path: Path, parent: Path) -> bool:
    resolved = path.resolve()
    allowed = parent.resolve()
    return resolved == allowed or allowed in resolved.parents


def _result(
    cfg: FileBasedImporterConfig,
    status: str,
    notes: str,
    *,
    input_path: Path | None = None,
    rows_input: int = 0,
    missing_required_columns: str = "",
) -> FileBasedImporterResult:
    path_text = str(input_path.resolve()) if input_path else str(cfg.input_path or "")
    return FileBasedImporterResult(
        source_id=cfg.source_id,
        contract_id=cfg.contract_id,
        input_path=path_text,
        output_path="",
        rows_input=int(rows_input),
        rows_normalized=0,
        missing_required_columns=missing_required_columns,
        network_calls_enabled=False,
        dry_run_status=status,
        recommendation=status,
        notes=notes,
    )

