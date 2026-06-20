# -*- coding: utf-8 -*-
"""Analysis input bundle preview builder."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

ANALYSIS_INPUT_BUNDLE_PREVIEW_READY = "ANALYSIS_INPUT_BUNDLE_PREVIEW_READY"
ANALYSIS_INPUT_BUNDLE_BLOCKED_MISSING_FILE = "ANALYSIS_INPUT_BUNDLE_BLOCKED_MISSING_FILE"
ANALYSIS_INPUT_BUNDLE_BLOCKED_MISSING_REQUIRED_COLUMNS = "ANALYSIS_INPUT_BUNDLE_BLOCKED_MISSING_REQUIRED_COLUMNS"
ANALYSIS_INPUT_BUNDLE_BLOCKED_MISSING_REQUIRED_VALUES = "ANALYSIS_INPUT_BUNDLE_BLOCKED_MISSING_REQUIRED_VALUES"
ANALYSIS_INPUT_BUNDLE_BLOCKED_UNSAFE_PATH = "ANALYSIS_INPUT_BUNDLE_BLOCKED_UNSAFE_PATH"
ANALYSIS_INPUT_BUNDLE_MODEL_DISABLED_BY_DESIGN = "ANALYSIS_INPUT_BUNDLE_MODEL_DISABLED_BY_DESIGN"
ANALYSIS_INPUT_BUNDLE_BETTING_DISABLED_BY_DESIGN = "ANALYSIS_INPUT_BUNDLE_BETTING_DISABLED_BY_DESIGN"

REQUIRED_CANONICAL_MATCH_FIELDS = [
    "source_id",
    "provider_match_id",
    "league",
    "season",
    "date",
    "home_team",
    "away_team",
    "home_goals",
    "away_goals",
    "match_status",
]

MANIFEST_COLUMNS = [
    "bundle_id",
    "source_id",
    "contract_id",
    "input_path",
    "output_path",
    "rows_input",
    "rows_ready",
    "missing_required_columns",
    "missing_required_values",
    "network_calls_enabled",
    "prediction_logic_enabled",
    "betting_logic_enabled",
    "bundle_status",
    "recommendation",
    "notes",
]


@dataclass(frozen=True)
class AnalysisInputBundleConfig:
    input_path: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/input_bundle"
    write_preview: bool = False
    base_dir: str | Path = "."
    bundle_id: str = "canonical_match_analysis_input_preview"
    source_id: str = "file_csv"
    contract_id: str = "canonical_match"


@dataclass(frozen=True)
class AnalysisInputBundleResult:
    bundle_id: str
    source_id: str
    contract_id: str
    input_path: str
    output_path: str
    rows_input: int
    rows_ready: int
    missing_required_columns: str
    missing_required_values: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    bundle_status: str
    recommendation: str
    notes: str


class AnalysisInputBundleBuilder:
    def __init__(self, config: AnalysisInputBundleConfig) -> None:
        self.config = config

    def build(self) -> tuple[AnalysisInputBundleResult, pd.DataFrame, pd.DataFrame]:
        cfg = self.config
        base = Path(cfg.base_dir).resolve()
        out_dir = _safe_output_dir(cfg.output_dir, base)
        if out_dir is None:
            result = _result(cfg, ANALYSIS_INPUT_BUNDLE_BLOCKED_UNSAFE_PATH, "OUTPUT_DIR_MUST_BE_UNDER_OUTPUTS_ANALYSIS_PREVIEW_INPUT_BUNDLE")
            return result, pd.DataFrame(), _validation_frame(result)

        input_path = Path(cfg.input_path) if cfg.input_path is not None else base / "outputs" / "importer_preview" / "normalized" / "canonical_match_preview.csv"
        if not input_path.is_absolute():
            input_path = base / input_path
        if not input_path.exists():
            result = _result(cfg, ANALYSIS_INPUT_BUNDLE_BLOCKED_MISSING_FILE, "INPUT_FILE_NOT_FOUND", input_path=input_path)
            return result, pd.DataFrame(), _validation_frame(result)

        try:
            source = pd.read_csv(input_path, low_memory=False)
        except Exception as exc:
            result = _result(cfg, ANALYSIS_INPUT_BUNDLE_BLOCKED_MISSING_FILE, f"INPUT_READ_FAILED:{exc}", input_path=input_path)
            return result, pd.DataFrame(), _validation_frame(result)

        missing_columns = [column for column in REQUIRED_CANONICAL_MATCH_FIELDS if column not in source.columns]
        if missing_columns:
            result = _result(
                cfg,
                ANALYSIS_INPUT_BUNDLE_BLOCKED_MISSING_REQUIRED_COLUMNS,
                "MISSING_REQUIRED_COLUMNS",
                input_path=input_path,
                rows_input=len(source),
                missing_required_columns=" | ".join(missing_columns),
            )
            return result, pd.DataFrame(), _validation_frame(result)

        missing_values = _missing_required_values(source)
        if missing_values:
            result = _result(
                cfg,
                ANALYSIS_INPUT_BUNDLE_BLOCKED_MISSING_REQUIRED_VALUES,
                "MISSING_REQUIRED_VALUES",
                input_path=input_path,
                rows_input=len(source),
                missing_required_values=" | ".join(missing_values),
            )
            return result, pd.DataFrame(), _validation_frame(result)

        ready = source[REQUIRED_CANONICAL_MATCH_FIELDS].copy()
        output_path = ""
        if cfg.write_preview:
            out_dir.mkdir(parents=True, exist_ok=True)
            candidate = (out_dir / "canonical_match_analysis_input_preview.csv").resolve()
            if not _is_under(candidate, out_dir):
                result = _result(cfg, ANALYSIS_INPUT_BUNDLE_BLOCKED_UNSAFE_PATH, "ANALYSIS_OUTPUT_OUTSIDE_PREVIEW_DIR", input_path=input_path, rows_input=len(source))
                return result, pd.DataFrame(), _validation_frame(result)
            ready.to_csv(candidate, index=False)
            output_path = str(candidate)

        result = AnalysisInputBundleResult(
            bundle_id=cfg.bundle_id,
            source_id=cfg.source_id,
            contract_id=cfg.contract_id,
            input_path=str(input_path.resolve()),
            output_path=output_path,
            rows_input=int(len(source)),
            rows_ready=int(len(ready)),
            missing_required_columns="",
            missing_required_values="",
            network_calls_enabled=False,
            prediction_logic_enabled=False,
            betting_logic_enabled=False,
            bundle_status=ANALYSIS_INPUT_BUNDLE_PREVIEW_READY,
            recommendation=ANALYSIS_INPUT_BUNDLE_PREVIEW_READY,
            notes=f"{ANALYSIS_INPUT_BUNDLE_MODEL_DISABLED_BY_DESIGN}; {ANALYSIS_INPUT_BUNDLE_BETTING_DISABLED_BY_DESIGN}",
        )
        return result, ready, _validation_frame(result)


def build_manifest_frame(result: AnalysisInputBundleResult) -> pd.DataFrame:
    return pd.DataFrame([result.__dict__], columns=MANIFEST_COLUMNS)


def build_manifest_markdown(result: AnalysisInputBundleResult) -> str:
    return "\n".join([
        "# Phase 16.1 Analysis Input Bundle Preview",
        "",
        "Phase 16.1 converts local importer preview output into an analysis-ready input bundle. No model predictions or betting logic are run.",
        "",
        "## A. Executive Summary",
        f"- analysis input bundle status: {result.bundle_status}",
        f"- rows input: {result.rows_input}",
        f"- rows ready: {result.rows_ready}",
        "- network calls enabled: false",
        "- prediction logic enabled: false",
        "- betting logic enabled: false",
        "",
        "## B. Safety Notes",
        "- Local/importer-preview files are consumed only for preview.",
        "- Missing values are not inferred or invented.",
        "- Importer outputs stay separate from model integration until a later explicit phase.",
        "- No model, probability, market, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "",
        "## C. Recommendation",
        result.recommendation,
        "",
    ])


def _missing_required_values(frame: pd.DataFrame) -> list[str]:
    missing: list[str] = []
    for column in REQUIRED_CANONICAL_MATCH_FIELDS:
        values = frame[column]
        blank = values.isna() | values.astype(str).str.strip().eq("")
        if bool(blank.any()):
            missing.append(column)
    return missing


def _safe_output_dir(output_dir: str | Path, base_dir: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base_dir / out
    resolved = out.resolve()
    allowed = (base_dir / "outputs" / "analysis_preview" / "input_bundle").resolve()
    if resolved == allowed or allowed in resolved.parents:
        return resolved
    return None


def _is_under(path: Path, parent: Path) -> bool:
    resolved = path.resolve()
    allowed = parent.resolve()
    return resolved == allowed or allowed in resolved.parents


def _validation_frame(result: AnalysisInputBundleResult) -> pd.DataFrame:
    return pd.DataFrame([{
        "bundle_id": result.bundle_id,
        "rows_input": result.rows_input,
        "rows_ready": result.rows_ready,
        "missing_required_columns": result.missing_required_columns,
        "missing_required_values": result.missing_required_values,
        "bundle_status": result.bundle_status,
        "network_calls_enabled": result.network_calls_enabled,
        "prediction_logic_enabled": result.prediction_logic_enabled,
        "betting_logic_enabled": result.betting_logic_enabled,
        "notes": result.notes,
    }])


def _result(
    cfg: AnalysisInputBundleConfig,
    status: str,
    notes: str,
    *,
    input_path: Path | None = None,
    rows_input: int = 0,
    missing_required_columns: str = "",
    missing_required_values: str = "",
) -> AnalysisInputBundleResult:
    path_text = str(input_path.resolve()) if input_path else str(cfg.input_path or "")
    return AnalysisInputBundleResult(
        bundle_id=cfg.bundle_id,
        source_id=cfg.source_id,
        contract_id=cfg.contract_id,
        input_path=path_text,
        output_path="",
        rows_input=int(rows_input),
        rows_ready=0,
        missing_required_columns=missing_required_columns,
        missing_required_values=missing_required_values,
        network_calls_enabled=False,
        prediction_logic_enabled=False,
        betting_logic_enabled=False,
        bundle_status=status,
        recommendation=status,
        notes=notes,
    )

