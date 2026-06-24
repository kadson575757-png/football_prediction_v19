# -*- coding: utf-8 -*-
"""Preview-only real match intake validation."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import pandas as pd
from pandas.errors import EmptyDataError

from football_prediction_v19.analysis.real_match_intake_schema_preview import INTAKE_COLUMNS

REAL_MATCH_INTAKE_VALIDATION_READY = "REAL_MATCH_INTAKE_VALIDATION_READY"
REAL_MATCH_INTAKE_VALIDATION_BLOCKED_MISSING_REQUIRED_COLUMNS = "REAL_MATCH_INTAKE_VALIDATION_BLOCKED_MISSING_REQUIRED_COLUMNS"
REAL_MATCH_INTAKE_VALIDATION_BLOCKED_EMPTY_REQUIRED_VALUES = "REAL_MATCH_INTAKE_VALIDATION_BLOCKED_EMPTY_REQUIRED_VALUES"
REAL_MATCH_INTAKE_VALIDATION_BLOCKED_DUPLICATE_MATCHES = "REAL_MATCH_INTAKE_VALIDATION_BLOCKED_DUPLICATE_MATCHES"
REAL_MATCH_INTAKE_VALIDATION_BLOCKED_UNSAFE_PATH = "REAL_MATCH_INTAKE_VALIDATION_BLOCKED_UNSAFE_PATH"
REAL_MATCH_INTAKE_VALIDATION_MANUAL_KEY_GENERATED = "REAL_MATCH_INTAKE_VALIDATION_MANUAL_KEY_GENERATED"
REAL_MATCH_INTAKE_VALIDATION_NO_BETTING_OUTPUT_BY_DESIGN = "REAL_MATCH_INTAKE_VALIDATION_NO_BETTING_OUTPUT_BY_DESIGN"

REQUIRED_COLUMNS = ["match_date", "competition", "season", "home_team", "away_team", "cross_provider_match_key"]
REQUIRED_VALUE_COLUMNS = ["match_date", "competition", "season", "home_team", "away_team"]
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class RealMatchIntakeValidationConfig:
    input_path: str | Path | None = None
    manual_key_generation_enabled: bool = False
    output_dir: str | Path = "outputs/analysis_preview/real_match_intake_validation"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class RealMatchIntakeValidationResult:
    real_match_intake_validation_run_id: str
    real_match_intake_validation_status: str
    rows_input: int
    rows_valid: int
    rows_invalid: int
    manual_key_generated: bool
    manual_review_required: bool
    output_path: str
    summary_path: str
    manifest_path: str
    recommendation: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool


class RealMatchIntakeValidator:
    def __init__(self, config: RealMatchIntakeValidationConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> RealMatchIntakeValidationResult:
        if self.config.input_path is None or _unsafe(self.config.input_path):
            return self._blocked(REAL_MATCH_INTAKE_VALIDATION_BLOCKED_UNSAFE_PATH)
        source = _resolve(self.config.input_path, self.base)
        out = _safe_output(self.config.output_dir, self.base)
        if out is None or source is None or _unsafe(source):
            return self._blocked(REAL_MATCH_INTAKE_VALIDATION_BLOCKED_UNSAFE_PATH)
        try:
            frame = pd.read_csv(source, low_memory=False, keep_default_na=False)
        except (FileNotFoundError, EmptyDataError):
            return self._blocked(REAL_MATCH_INTAKE_VALIDATION_BLOCKED_MISSING_REQUIRED_COLUMNS)
        missing_columns = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
        if missing_columns:
            return self._blocked(REAL_MATCH_INTAKE_VALIDATION_BLOCKED_MISSING_REQUIRED_COLUMNS, rows_input=len(frame))
        for column in INTAKE_COLUMNS:
            if column not in frame.columns:
                frame[column] = ""
        if frame.empty or any(frame[c].astype(str).str.strip().eq("").any() for c in REQUIRED_VALUE_COLUMNS):
            return self._blocked(REAL_MATCH_INTAKE_VALIDATION_BLOCKED_EMPTY_REQUIRED_VALUES, rows_input=len(frame))
        manual_generated = False
        empty_keys = frame["cross_provider_match_key"].astype(str).str.strip().eq("")
        if empty_keys.any():
            if not self.config.manual_key_generation_enabled:
                return self._blocked(REAL_MATCH_INTAKE_VALIDATION_BLOCKED_EMPTY_REQUIRED_VALUES, rows_input=len(frame))
            frame.loc[empty_keys, "cross_provider_match_key"] = frame[empty_keys].apply(_manual_key, axis=1)
            manual_generated = True
        if frame["cross_provider_match_key"].astype(str).str.lower().duplicated().any():
            return self._blocked(REAL_MATCH_INTAKE_VALIDATION_BLOCKED_DUPLICATE_MATCHES, rows_input=len(frame))
        if len(frame) != 1:
            duplicate_selector = frame[REQUIRED_VALUE_COLUMNS].astype(str).agg("|".join, axis=1).str.lower().duplicated().any()
            if duplicate_selector or len(frame) > 1:
                return self._blocked(REAL_MATCH_INTAKE_VALIDATION_BLOCKED_DUPLICATE_MATCHES, rows_input=len(frame))
        frame["real_match_intake_validation_status"] = REAL_MATCH_INTAKE_VALIDATION_READY
        frame["manual_key_generated"] = manual_generated
        frame["manual_review_required"] = frame.get("manual_review_required", "true")
        for column in ["network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
            frame[column] = False
        out.mkdir(parents=True, exist_ok=True)
        output_path = out / "real_match_intake_validation.csv"
        summary_path = out / "real_match_intake_validation_summary.md"
        manifest_path = out / "real_match_intake_validation_manifest.csv"
        frame.to_csv(output_path, index=False)
        result = RealMatchIntakeValidationResult(
            "real_match_intake_validation_preview", REAL_MATCH_INTAKE_VALIDATION_READY,
            len(frame), len(frame), 0, manual_generated, _truthy(frame.iloc[0].get("manual_review_required", True)),
            str(output_path.resolve()), str(summary_path.resolve()), str(manifest_path.resolve()),
            REAL_MATCH_INTAKE_VALIDATION_READY, False, False, False, False, False,
        )
        pd.DataFrame([result.__dict__]).to_csv(manifest_path, index=False)
        summary_path.write_text("\n".join([
            "# Real Match Intake Validation Preview", "",
            f"- real_match_intake_validation_status: {result.real_match_intake_validation_status}",
            f"- rows_valid: {result.rows_valid}",
            f"- manual_key_generated: {str(result.manual_key_generated).lower()}",
            "- optional evidence remains blank when missing; no values are inferred",
            "- no production prediction, betting output, position sizing, or financial return tracking", "",
        ]), encoding="utf-8")
        return result

    def _blocked(self, status: str, *, rows_input: int = 0) -> RealMatchIntakeValidationResult:
        return RealMatchIntakeValidationResult("real_match_intake_validation_preview", status, rows_input, 0, rows_input, False, False, "", "", "", status, False, False, False, False, False)


def _manual_key(row: pd.Series) -> str:
    return "manual-{competition}-{season}-{home}-{away}-{date}".format(
        competition=_slug(row.get("competition", "")),
        season=_slug(row.get("season", "")),
        home=_slug(row.get("home_team", "")),
        away=_slug(row.get("away_team", "")),
        date=str(row.get("match_date", ""))[:10],
    )


def _slug(value: object) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower())
    return text.strip("-") or "unknown"


def _truthy(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _resolve(path: str | Path | None, base: Path) -> Path | None:
    if path is None or str(path).strip() == "":
        return None
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "real_match_intake_validation").resolve()
    return resolved if resolved == allowed or allowed in resolved.parents else None


def _unsafe(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return text.startswith(("http://", "https://")) or any(token in text for token in PROTECTED)
