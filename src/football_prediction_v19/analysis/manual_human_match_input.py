# -*- coding: utf-8 -*-
"""Manual human match input template and validation preview."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

MANUAL_HUMAN_MATCH_INPUT_TEMPLATE_READY = "MANUAL_HUMAN_MATCH_INPUT_TEMPLATE_READY"
MANUAL_HUMAN_MATCH_INPUT_EXAMPLE_READY = "MANUAL_HUMAN_MATCH_INPUT_EXAMPLE_READY"
MANUAL_HUMAN_MATCH_INPUT_VALIDATION_READY = "MANUAL_HUMAN_MATCH_INPUT_VALIDATION_READY"
MANUAL_HUMAN_MATCH_INPUT_VALIDATION_PARTIAL_READY = "MANUAL_HUMAN_MATCH_INPUT_VALIDATION_PARTIAL_READY"
MANUAL_HUMAN_MATCH_INPUT_BLOCKED_MISSING_REQUIRED_COLUMNS = "MANUAL_HUMAN_MATCH_INPUT_BLOCKED_MISSING_REQUIRED_COLUMNS"
MANUAL_HUMAN_MATCH_INPUT_BLOCKED_EMPTY_REQUIRED_VALUES = "MANUAL_HUMAN_MATCH_INPUT_BLOCKED_EMPTY_REQUIRED_VALUES"
MANUAL_HUMAN_MATCH_INPUT_BLOCKED_DUPLICATE_MATCH_IDS = "MANUAL_HUMAN_MATCH_INPUT_BLOCKED_DUPLICATE_MATCH_IDS"
MANUAL_HUMAN_MATCH_INPUT_BLOCKED_UNSAFE_PATH = "MANUAL_HUMAN_MATCH_INPUT_BLOCKED_UNSAFE_PATH"
MANUAL_HUMAN_MATCH_INPUT_OPTIONAL_CONTEXT_MISSING = "MANUAL_HUMAN_MATCH_INPUT_OPTIONAL_CONTEXT_MISSING"
MANUAL_HUMAN_MATCH_INPUT_EXTRA_COLUMNS_WARNING = "MANUAL_HUMAN_MATCH_INPUT_EXTRA_COLUMNS_WARNING"
MANUAL_HUMAN_MATCH_INPUT_NETWORK_DISABLED_BY_DESIGN = "MANUAL_HUMAN_MATCH_INPUT_NETWORK_DISABLED_BY_DESIGN"
MANUAL_HUMAN_MATCH_INPUT_MODEL_DISABLED_BY_DESIGN = "MANUAL_HUMAN_MATCH_INPUT_MODEL_DISABLED_BY_DESIGN"
MANUAL_HUMAN_MATCH_INPUT_BETTING_DISABLED_BY_DESIGN = "MANUAL_HUMAN_MATCH_INPUT_BETTING_DISABLED_BY_DESIGN"

REQUIRED_COLUMNS = [
    "source_id", "provider_match_id", "league", "season", "match_date",
    "date", "home_team", "away_team", "home_goals", "away_goals", "match_status",
]
OPTIONAL_COLUMNS = [
    "venue", "neutral_venue", "home_xg", "away_xg", "home_xga", "away_xga",
    "home_recent_xg", "away_recent_xg", "home_recent_xga", "away_recent_xga",
    "home_big_chances", "away_big_chances", "home_notes", "away_notes",
    "market_notes", "injury_notes", "tactical_notes", "data_quality_notes",
]
ALL_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS
PROTECTED_PATH_TOKENS = [
    "data/processed",
    "trusted_xg_sources/accepted",
    "trusted_xg_sources/raw",
    "manual_xg_manifest",
]


@dataclass(frozen=True)
class ManualHumanMatchInputConfig:
    input_path: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/manual_input"
    base_dir: str | Path = "."
    allow_extra_columns: bool = True


@dataclass(frozen=True)
class ManualHumanMatchInputValidationResult:
    validation_status: str
    rows_input: int
    rows_valid: int
    rows_invalid: int
    required_columns_present: bool
    optional_columns_present: int
    missing_required_columns: str
    empty_required_values: str
    duplicate_match_ids: str
    extra_columns_count: int
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    recommendation: str
    notes: str


class ManualHumanMatchInputTemplateBuilder:
    def __init__(self, config: ManualHumanMatchInputConfig) -> None:
        self.config = config

    def output_dir(self) -> Path | None:
        return _safe_output_dir(self.config.output_dir, Path(self.config.base_dir).resolve())

    def template_frame(self) -> pd.DataFrame:
        return pd.DataFrame(columns=ALL_COLUMNS)

    def example_frame(self) -> pd.DataFrame:
        row: dict[str, Any] = {column: "" for column in ALL_COLUMNS}
        row.update({
            "source_id": "manual_csv",
            "provider_match_id": "manual-preview-1",
            "league": "Preview League",
            "season": "2024",
            "match_date": "2024-08-23",
            "date": "2024-08-23",
            "home_team": "Home FC",
            "away_team": "Away FC",
            "home_goals": 2,
            "away_goals": 1,
            "match_status": "finished",
            "data_quality_notes": "Manual preview example only.",
        })
        return pd.DataFrame([row], columns=ALL_COLUMNS)

    def write(self) -> dict[str, Any]:
        out = self.output_dir()
        if out is None:
            return {"template_status": MANUAL_HUMAN_MATCH_INPUT_BLOCKED_UNSAFE_PATH, "example_status": MANUAL_HUMAN_MATCH_INPUT_BLOCKED_UNSAFE_PATH, "template_path": "", "example_path": ""}
        out.mkdir(parents=True, exist_ok=True)
        template = out / "manual_human_match_input_template.csv"
        example = out / "manual_human_match_input_example.csv"
        self.template_frame().to_csv(template, index=False)
        self.example_frame().to_csv(example, index=False)
        return {"template_status": MANUAL_HUMAN_MATCH_INPUT_TEMPLATE_READY, "example_status": MANUAL_HUMAN_MATCH_INPUT_EXAMPLE_READY, "template_path": str(template.resolve()), "example_path": str(example.resolve())}


class ManualHumanMatchInputValidator:
    def __init__(self, config: ManualHumanMatchInputConfig) -> None:
        self.config = config

    def validate(self) -> tuple[ManualHumanMatchInputValidationResult, pd.DataFrame]:
        base = Path(self.config.base_dir).resolve()
        out = _safe_output_dir(self.config.output_dir, base)
        path = Path(self.config.input_path) if self.config.input_path is not None else None
        if out is None or path is None:
            return _validation_result(MANUAL_HUMAN_MATCH_INPUT_BLOCKED_UNSAFE_PATH), pd.DataFrame()
        if not path.is_absolute():
            path = base / path
        if _unsafe_input_path(path):
            return _validation_result(MANUAL_HUMAN_MATCH_INPUT_BLOCKED_UNSAFE_PATH), pd.DataFrame()
        try:
            if not path.exists():
                return _validation_result(MANUAL_HUMAN_MATCH_INPUT_BLOCKED_UNSAFE_PATH), pd.DataFrame()
            frame = pd.read_csv(path, low_memory=False)
        except Exception as exc:
            return _validation_result(MANUAL_HUMAN_MATCH_INPUT_BLOCKED_UNSAFE_PATH, notes=str(exc)), pd.DataFrame()
        missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
        extra = [column for column in frame.columns if column not in ALL_COLUMNS]
        optional_present = len([column for column in OPTIONAL_COLUMNS if column in frame.columns])
        if missing:
            return _validation_result(MANUAL_HUMAN_MATCH_INPUT_BLOCKED_MISSING_REQUIRED_COLUMNS, len(frame), missing_required_columns=" | ".join(missing), optional_columns_present=optional_present, extra_columns_count=len(extra)), frame
        empty_cols = [column for column in REQUIRED_COLUMNS if bool((frame[column].isna() | frame[column].astype(str).str.strip().eq("")).any())]
        if empty_cols:
            return _validation_result(MANUAL_HUMAN_MATCH_INPUT_BLOCKED_EMPTY_REQUIRED_VALUES, len(frame), empty_required_values=" | ".join(empty_cols), optional_columns_present=optional_present, extra_columns_count=len(extra)), frame
        duplicates = frame.loc[frame["provider_match_id"].astype(str).duplicated(keep=False), "provider_match_id"].astype(str).unique().tolist()
        if duplicates:
            return _validation_result(MANUAL_HUMAN_MATCH_INPUT_BLOCKED_DUPLICATE_MATCH_IDS, len(frame), duplicate_match_ids=" | ".join(duplicates), optional_columns_present=optional_present, extra_columns_count=len(extra)), frame
        notes = []
        if optional_present < len(OPTIONAL_COLUMNS):
            notes.append(MANUAL_HUMAN_MATCH_INPUT_OPTIONAL_CONTEXT_MISSING)
        if extra:
            notes.append(MANUAL_HUMAN_MATCH_INPUT_EXTRA_COLUMNS_WARNING + ":" + " | ".join(extra))
        return _validation_result(MANUAL_HUMAN_MATCH_INPUT_VALIDATION_READY, len(frame), rows_valid=len(frame), optional_columns_present=optional_present, extra_columns_count=len(extra), notes="; ".join(notes)), frame

    def write_outputs(self, result: ManualHumanMatchInputValidationResult) -> dict[str, str]:
        out = _safe_output_dir(self.config.output_dir, Path(self.config.base_dir).resolve())
        if out is None:
            return {"summary_path": "", "manifest_path": "", "markdown_path": ""}
        out.mkdir(parents=True, exist_ok=True)
        summary = out / "manual_human_match_input_validation_summary.csv"
        manifest = out / "manual_human_match_input_validation_manifest.csv"
        markdown = out / "manual_human_match_input_validation.md"
        pd.DataFrame([result.__dict__]).to_csv(summary, index=False)
        pd.DataFrame([result.__dict__]).to_csv(manifest, index=False)
        markdown.write_text(_markdown(result), encoding="utf-8")
        return {"summary_path": str(summary.resolve()), "manifest_path": str(manifest.resolve()), "markdown_path": str(markdown.resolve())}


def _validation_result(status: str, rows_input: int = 0, *, rows_valid: int = 0, missing_required_columns: str = "", empty_required_values: str = "", duplicate_match_ids: str = "", optional_columns_present: int = 0, extra_columns_count: int = 0, notes: str = "") -> ManualHumanMatchInputValidationResult:
    return ManualHumanMatchInputValidationResult(
        validation_status=status,
        rows_input=rows_input,
        rows_valid=rows_valid,
        rows_invalid=max(rows_input - rows_valid, 0),
        required_columns_present=not bool(missing_required_columns),
        optional_columns_present=optional_columns_present,
        missing_required_columns=missing_required_columns,
        empty_required_values=empty_required_values,
        duplicate_match_ids=duplicate_match_ids,
        extra_columns_count=extra_columns_count,
        network_calls_enabled=False,
        prediction_logic_enabled=False,
        betting_logic_enabled=False,
        recommendation=status,
        notes=notes or f"{MANUAL_HUMAN_MATCH_INPUT_NETWORK_DISABLED_BY_DESIGN}; {MANUAL_HUMAN_MATCH_INPUT_MODEL_DISABLED_BY_DESIGN}; {MANUAL_HUMAN_MATCH_INPUT_BETTING_DISABLED_BY_DESIGN}",
    )


def _safe_output_dir(output_dir: str | Path, base_dir: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base_dir / out
    resolved = out.resolve()
    allowed = (base_dir / "outputs" / "analysis_preview" / "manual_input").resolve()
    if resolved == allowed or allowed in resolved.parents:
        return resolved
    return None


def _unsafe_input_path(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    if text.startswith(("http://", "https://")):
        return True
    return any(token in text for token in PROTECTED_PATH_TOKENS)


def _markdown(result: ManualHumanMatchInputValidationResult) -> str:
    return "\n".join([
        "# Manual Human Match Input Validation Preview",
        "",
        f"- validation_status: {result.validation_status}",
        f"- rows_input: {result.rows_input}",
        f"- rows_valid: {result.rows_valid}",
        "- no live network calls",
        "- no model predictions are run",
        "- no betting/staking recommendations are generated",
        "- optional context is reported when missing and never inferred",
        "",
    ])
