# -*- coding: utf-8 -*-
"""Bridge match context bundle preview rows into human analysis input."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.match_context_bundle_preview import BUNDLE_COLUMNS

CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY = "CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY"
CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_MISSING_CONTEXT_INPUT = "CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_MISSING_CONTEXT_INPUT"
CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_UNKNOWN_MATCH = "CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_UNKNOWN_MATCH"
CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_AMBIGUOUS_MATCH = "CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_AMBIGUOUS_MATCH"
CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_MISSING_REQUIRED_COLUMNS = "CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_MISSING_REQUIRED_COLUMNS"
CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_MISSING_REQUIRED_VALUES = "CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_MISSING_REQUIRED_VALUES"
CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_UNSAFE_PATH = "CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_UNSAFE_PATH"
CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_OPTIONAL_VALUES_MISSING = "CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_OPTIONAL_VALUES_MISSING"
CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_NO_MODEL_INTEGRATION_BY_DESIGN = "CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_NO_MODEL_INTEGRATION_BY_DESIGN"
CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_NO_BETTING_INTEGRATION_BY_DESIGN = "CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_NO_BETTING_INTEGRATION_BY_DESIGN"
CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_NETWORK_DISABLED_BY_DESIGN = "CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_NETWORK_DISABLED_BY_DESIGN"

HUMAN_INPUT_COLUMNS = [
    "analysis_input_id", "context_bundle_id", "match_date", "competition", "season",
    "home_team", "away_team", "understat_provider_match_id", "fbref_provider_match_id",
    "cross_provider_match_key", "home_goals", "away_goals", "home_xg", "away_xg",
    "home_xga", "away_xga", "home_possession", "away_possession", "home_shots",
    "away_shots", "home_shots_on_target", "away_shots_on_target",
    "home_pass_completion_pct", "away_pass_completion_pct", "home_progressive_passes",
    "away_progressive_passes", "home_progressive_carries", "away_progressive_carries",
    "home_touches_att_pen_area", "away_touches_att_pen_area", "home_tackles",
    "away_tackles", "home_interceptions", "away_interceptions", "home_blocks",
    "away_blocks", "home_clearances", "away_clearances", "understat_data_quality_status",
    "fbref_data_quality_status", "context_data_quality_status", "missing_required_fields",
    "missing_optional_fields", "normalization_warning", "analysis_input_status",
    "recommendation", "notes", "network_calls_enabled", "prediction_logic_enabled",
    "betting_logic_enabled",
]
MANIFEST_COLUMNS = [
    "context_bridge_run_id", "match_context_bundle_path", "human_input_output_path",
    "rows_context", "rows_written", "candidates_checked", "candidates_matched",
    "missing_required_fields_count", "missing_optional_fields_count",
    "context_bridge_status", "recommendation", "notes", "network_calls_enabled",
    "prediction_logic_enabled", "betting_logic_enabled",
]
REQUIRED_COLUMNS = [
    "context_bundle_id", "match_date", "competition", "season", "home_team", "away_team",
    "understat_provider_match_id", "fbref_provider_match_id",
]
OPTIONAL_COLUMNS = [column for column in HUMAN_INPUT_COLUMNS if column not in REQUIRED_COLUMNS and column not in {"analysis_input_id", "analysis_input_status", "recommendation", "notes", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "missing_required_fields", "missing_optional_fields", "normalization_warning"}]
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class ContextBundleHumanInputBridgeConfig:
    match_context_bundle_path: str | Path | None = None
    context_bundle_id: str | None = None
    understat_provider_match_id: str | None = None
    fbref_provider_match_id: str | None = None
    cross_provider_match_key: str | None = None
    home_team: str | None = None
    away_team: str | None = None
    match_date: str | None = None
    competition: str | None = None
    season: str | None = None
    output_dir: str | Path = "outputs/analysis_preview/context_bundle_human_input"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class ContextBundleHumanInputBridgeResult:
    context_bridge_run_id: str
    match_context_bundle_path: str
    human_input_output_path: str
    manifest_path: str
    summary_path: str
    rows_context: int
    rows_written: int
    candidates_checked: int
    candidates_matched: int
    missing_required_fields_count: int
    missing_optional_fields_count: int
    context_bridge_status: str
    recommendation: str
    notes: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    context_bundle_id: str = ""
    understat_provider_match_id: str = ""
    fbref_provider_match_id: str = ""
    cross_provider_match_key: str = ""
    home_team: str = ""
    away_team: str = ""
    match_date: str = ""


class ContextBundleHumanInputBridgeRunner:
    def __init__(self, config: ContextBundleHumanInputBridgeConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> tuple[ContextBundleHumanInputBridgeResult, pd.DataFrame]:
        out = _safe_output(self.config.output_dir, self.base)
        if out is None:
            return self._blocked(CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_UNSAFE_PATH), pd.DataFrame(columns=HUMAN_INPUT_COLUMNS)
        source = _resolve(self.config.match_context_bundle_path, self.base)
        if source is None:
            source = self.base / "outputs" / "analysis_preview" / "match_context_bundle" / "match_context_bundle.csv"
        if _unsafe(source):
            return self._blocked(CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_UNSAFE_PATH), pd.DataFrame(columns=HUMAN_INPUT_COLUMNS)
        if not source.exists():
            return self._blocked(CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_MISSING_CONTEXT_INPUT, source=source), pd.DataFrame(columns=HUMAN_INPUT_COLUMNS)
        context = pd.read_csv(source, low_memory=False)
        missing_columns = [column for column in REQUIRED_COLUMNS if column not in context.columns]
        if missing_columns:
            return self._blocked(CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_MISSING_REQUIRED_COLUMNS, source=source, rows_context=len(context), notes=" | ".join(missing_columns)), pd.DataFrame(columns=HUMAN_INPUT_COLUMNS)
        missing_required = _missing_value_count(context, REQUIRED_COLUMNS)
        if missing_required:
            return self._blocked(CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_MISSING_REQUIRED_VALUES, source=source, rows_context=len(context), missing_required=missing_required), pd.DataFrame(columns=HUMAN_INPUT_COLUMNS)
        selected = _filter(context, self.config)
        if len(selected) == 0:
            return self._blocked(CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_UNKNOWN_MATCH, source=source, rows_context=len(context), candidates_checked=len(context)), pd.DataFrame(columns=HUMAN_INPUT_COLUMNS)
        if len(selected) > 1:
            return self._blocked(CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_BLOCKED_AMBIGUOUS_MATCH, source=source, rows_context=len(context), candidates_checked=len(context), candidates_matched=len(selected)), pd.DataFrame(columns=HUMAN_INPUT_COLUMNS)
        row = _human_row(selected.iloc[0])
        missing_optional = len([field for field in str(row["missing_optional_fields"]).split(" | ") if field])
        if missing_optional:
            row["normalization_warning"] = _append_warning(row["normalization_warning"], CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_OPTIONAL_VALUES_MISSING)
        human = pd.DataFrame([{**row, "analysis_input_status": CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY, "recommendation": CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY, "notes": _notes(), "network_calls_enabled": False, "prediction_logic_enabled": False, "betting_logic_enabled": False}], columns=HUMAN_INPUT_COLUMNS)
        out.mkdir(parents=True, exist_ok=True)
        output_path = out / "context_bundle_human_input.csv"
        manifest_path = out / "context_bundle_human_input_manifest.csv"
        summary_path = out / "context_bundle_human_input_summary.md"
        human.to_csv(output_path, index=False)
        result = ContextBundleHumanInputBridgeResult(
            context_bridge_run_id="context_bundle_human_input_bridge_preview",
            match_context_bundle_path=str(source.resolve()),
            human_input_output_path=str(output_path.resolve()),
            manifest_path=str(manifest_path.resolve()),
            summary_path=str(summary_path.resolve()),
            rows_context=len(context),
            rows_written=1,
            candidates_checked=len(context),
            candidates_matched=1,
            missing_required_fields_count=0,
            missing_optional_fields_count=missing_optional,
            context_bridge_status=CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY,
            recommendation=CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_PREVIEW_READY,
            notes=_notes(),
            network_calls_enabled=False,
            prediction_logic_enabled=False,
            betting_logic_enabled=False,
            context_bundle_id=str(row["context_bundle_id"]),
            understat_provider_match_id=str(row["understat_provider_match_id"]),
            fbref_provider_match_id=str(row["fbref_provider_match_id"]),
            cross_provider_match_key=str(row["cross_provider_match_key"]),
            home_team=str(row["home_team"]),
            away_team=str(row["away_team"]),
            match_date=str(row["match_date"]),
        )
        pd.DataFrame([{column: getattr(result, column) for column in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest_path, index=False)
        summary_path.write_text(f"# Context Bundle Human Input Bridge Preview\n\n- context_bridge_status: {result.context_bridge_status}\n- rows_written: 1\n", encoding="utf-8")
        return result, human

    def _blocked(self, status: str, *, source: Path | None = None, rows_context: int = 0, candidates_checked: int = 0, candidates_matched: int = 0, missing_required: int = 0, notes: str = "") -> ContextBundleHumanInputBridgeResult:
        return ContextBundleHumanInputBridgeResult(
            context_bridge_run_id="context_bundle_human_input_bridge_preview",
            match_context_bundle_path=str(source or self.config.match_context_bundle_path or ""),
            human_input_output_path="",
            manifest_path="",
            summary_path="",
            rows_context=rows_context,
            rows_written=0,
            candidates_checked=candidates_checked,
            candidates_matched=candidates_matched,
            missing_required_fields_count=missing_required,
            missing_optional_fields_count=0,
            context_bridge_status=status,
            recommendation=status,
            notes=notes or _notes(),
            network_calls_enabled=False,
            prediction_logic_enabled=False,
            betting_logic_enabled=False,
        )


def _filter(frame: pd.DataFrame, config: ContextBundleHumanInputBridgeConfig) -> pd.DataFrame:
    selected = frame.copy()
    for column, value in [
        ("context_bundle_id", config.context_bundle_id),
        ("understat_provider_match_id", config.understat_provider_match_id),
        ("fbref_provider_match_id", config.fbref_provider_match_id),
        ("cross_provider_match_key", config.cross_provider_match_key),
        ("match_date", config.match_date[:10] if config.match_date else None),
        ("competition", config.competition),
        ("season", config.season),
        ("home_team", config.home_team),
        ("away_team", config.away_team),
    ]:
        if value:
            if column == "match_date":
                selected = selected[selected[column].astype(str).str[:10] == str(value)]
            else:
                selected = selected[selected[column].astype(str).str.lower() == str(value).lower()]
    return selected


def _human_row(row: pd.Series) -> dict[str, object]:
    values = {column: "" for column in HUMAN_INPUT_COLUMNS}
    values.update({column: row.get(column, "") for column in HUMAN_INPUT_COLUMNS if column in row.index})
    values["analysis_input_id"] = "context_bundle_human_input_preview"
    missing_optional = [column for column in OPTIONAL_COLUMNS if _blank(values.get(column, ""))]
    values["missing_required_fields"] = str(row.get("missing_required_fields", ""))
    existing_missing = [part for part in str(row.get("missing_optional_fields", "")).split(" | ") if part]
    values["missing_optional_fields"] = " | ".join(sorted(set(existing_missing + missing_optional)))
    values["normalization_warning"] = str(row.get("normalization_warning", ""))
    return values


def _append_warning(existing: object, warning: str) -> str:
    parts = [str(existing).strip()] if not _blank(existing) else []
    parts.append(warning)
    return " | ".join(parts)


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "context_bundle_human_input").resolve()
    return resolved if resolved == allowed or allowed in resolved.parents else None


def _resolve(path: str | Path | None, base: Path) -> Path | None:
    if path is None:
        return None
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _unsafe(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return text.startswith(("http://", "https://")) or any(token in text for token in PROTECTED)


def _missing_value_count(frame: pd.DataFrame, columns: list[str]) -> int:
    if frame.empty:
        return 0
    mask = pd.Series(False, index=frame.index)
    for column in columns:
        mask = mask | frame[column].isna() | frame[column].astype(str).str.strip().eq("")
    return int(mask.sum())


def _blank(value: object) -> bool:
    if pd.isna(value):
        return True
    return str(value).strip() == ""


def _notes() -> str:
    return "; ".join([
        CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_NETWORK_DISABLED_BY_DESIGN,
        CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_NO_MODEL_INTEGRATION_BY_DESIGN,
        CONTEXT_BUNDLE_HUMAN_INPUT_BRIDGE_NO_BETTING_INTEGRATION_BY_DESIGN,
    ])
