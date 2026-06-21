# -*- coding: utf-8 -*-
"""Render preview-only context-enriched human match report."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.context_bundle_human_input_bridge_preview import HUMAN_INPUT_COLUMNS

CONTEXT_ENRICHED_HUMAN_REPORT_PREVIEW_READY = "CONTEXT_ENRICHED_HUMAN_REPORT_PREVIEW_READY"
CONTEXT_ENRICHED_HUMAN_REPORT_BLOCKED_MISSING_INPUT = "CONTEXT_ENRICHED_HUMAN_REPORT_BLOCKED_MISSING_INPUT"
CONTEXT_ENRICHED_HUMAN_REPORT_BLOCKED_MISSING_REQUIRED_COLUMNS = "CONTEXT_ENRICHED_HUMAN_REPORT_BLOCKED_MISSING_REQUIRED_COLUMNS"
CONTEXT_ENRICHED_HUMAN_REPORT_BLOCKED_MISSING_REQUIRED_VALUES = "CONTEXT_ENRICHED_HUMAN_REPORT_BLOCKED_MISSING_REQUIRED_VALUES"
CONTEXT_ENRICHED_HUMAN_REPORT_BLOCKED_UNSAFE_PATH = "CONTEXT_ENRICHED_HUMAN_REPORT_BLOCKED_UNSAFE_PATH"
CONTEXT_ENRICHED_HUMAN_REPORT_OPTIONAL_VALUES_MISSING = "CONTEXT_ENRICHED_HUMAN_REPORT_OPTIONAL_VALUES_MISSING"
CONTEXT_ENRICHED_HUMAN_REPORT_NO_MODEL_INTEGRATION_BY_DESIGN = "CONTEXT_ENRICHED_HUMAN_REPORT_NO_MODEL_INTEGRATION_BY_DESIGN"
CONTEXT_ENRICHED_HUMAN_REPORT_NO_BETTING_INTEGRATION_BY_DESIGN = "CONTEXT_ENRICHED_HUMAN_REPORT_NO_BETTING_INTEGRATION_BY_DESIGN"
CONTEXT_ENRICHED_HUMAN_REPORT_NETWORK_DISABLED_BY_DESIGN = "CONTEXT_ENRICHED_HUMAN_REPORT_NETWORK_DISABLED_BY_DESIGN"

MANIFEST_COLUMNS = [
    "context_report_run_id", "context_human_input_path", "report_output_path",
    "rows_input", "rows_reported", "sections_rendered", "missing_required_fields_count",
    "missing_optional_fields_count", "context_report_status", "recommendation", "notes",
    "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled",
]
REQUIRED_COLUMNS = ["analysis_input_id", "match_date", "competition", "season", "home_team", "away_team", "understat_provider_match_id", "fbref_provider_match_id"]
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class ContextEnrichedHumanReportConfig:
    context_human_input_path: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/context_enriched_human_report"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class ContextEnrichedHumanReportResult:
    context_report_run_id: str
    context_human_input_path: str
    report_output_path: str
    manifest_path: str
    rows_input: int
    rows_reported: int
    sections_rendered: int
    missing_required_fields_count: int
    missing_optional_fields_count: int
    context_report_status: str
    recommendation: str
    notes: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool


class ContextEnrichedHumanReportRunner:
    def __init__(self, config: ContextEnrichedHumanReportConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> tuple[ContextEnrichedHumanReportResult, str]:
        out = _safe_output(self.config.output_dir, self.base)
        if out is None:
            return self._blocked(CONTEXT_ENRICHED_HUMAN_REPORT_BLOCKED_UNSAFE_PATH), ""
        source = _resolve(self.config.context_human_input_path, self.base)
        if source is None:
            source = self.base / "outputs" / "analysis_preview" / "context_bundle_human_input" / "context_bundle_human_input.csv"
        if _unsafe(source):
            return self._blocked(CONTEXT_ENRICHED_HUMAN_REPORT_BLOCKED_UNSAFE_PATH), ""
        if not source.exists():
            return self._blocked(CONTEXT_ENRICHED_HUMAN_REPORT_BLOCKED_MISSING_INPUT, source=source), ""
        frame = pd.read_csv(source, low_memory=False)
        missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
        if missing_columns:
            return self._blocked(CONTEXT_ENRICHED_HUMAN_REPORT_BLOCKED_MISSING_REQUIRED_COLUMNS, source=source, rows_input=len(frame), notes=" | ".join(missing_columns)), ""
        missing_required = _missing_value_count(frame, REQUIRED_COLUMNS)
        if missing_required:
            return self._blocked(CONTEXT_ENRICHED_HUMAN_REPORT_BLOCKED_MISSING_REQUIRED_VALUES, source=source, rows_input=len(frame), missing_required=missing_required), ""
        if len(frame) != 1:
            return self._blocked(CONTEXT_ENRICHED_HUMAN_REPORT_BLOCKED_MISSING_REQUIRED_VALUES, source=source, rows_input=len(frame), missing_required=0, notes="Expected exactly one human input row"), ""
        row = frame.iloc[0]
        missing_optional = len([part for part in str(row.get("missing_optional_fields", "")).split(" | ") if part])
        report, sections = _render_report(row)
        out.mkdir(parents=True, exist_ok=True)
        report_path = out / "context_enriched_human_match_report_preview.md"
        manifest_path = out / "context_enriched_human_match_report_manifest.csv"
        report_path.write_text(report, encoding="utf-8")
        result = ContextEnrichedHumanReportResult(
            context_report_run_id="context_enriched_human_report_preview",
            context_human_input_path=str(source.resolve()),
            report_output_path=str(report_path.resolve()),
            manifest_path=str(manifest_path.resolve()),
            rows_input=len(frame),
            rows_reported=1,
            sections_rendered=sections,
            missing_required_fields_count=0,
            missing_optional_fields_count=missing_optional,
            context_report_status=CONTEXT_ENRICHED_HUMAN_REPORT_PREVIEW_READY,
            recommendation=CONTEXT_ENRICHED_HUMAN_REPORT_PREVIEW_READY,
            notes=_notes(missing_optional),
            network_calls_enabled=False,
            prediction_logic_enabled=False,
            betting_logic_enabled=False,
        )
        pd.DataFrame([{column: getattr(result, column) for column in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest_path, index=False)
        return result, report

    def _blocked(self, status: str, *, source: Path | None = None, rows_input: int = 0, missing_required: int = 0, notes: str = "") -> ContextEnrichedHumanReportResult:
        return ContextEnrichedHumanReportResult(
            context_report_run_id="context_enriched_human_report_preview",
            context_human_input_path=str(source or self.config.context_human_input_path or ""),
            report_output_path="",
            manifest_path="",
            rows_input=rows_input,
            rows_reported=0,
            sections_rendered=0,
            missing_required_fields_count=missing_required,
            missing_optional_fields_count=0,
            context_report_status=status,
            recommendation=status,
            notes=notes or _notes(0),
            network_calls_enabled=False,
            prediction_logic_enabled=False,
            betting_logic_enabled=False,
        )


def _render_report(row: pd.Series) -> tuple[str, int]:
    def v(column: str) -> str:
        value = row.get(column, "")
        if pd.isna(value) or str(value).strip() == "":
            return "not provided"
        return str(value)

    sections = [
        ("Match identity", f"{v('home_team')} vs {v('away_team')} on {v('match_date')} ({v('competition')} {v('season')})."),
        ("Data quality", f"Understat: {v('understat_data_quality_status')}; FBref: {v('fbref_data_quality_status')}; context: {v('context_data_quality_status')}."),
        ("Understat xG/xGA snapshot", f"Home xG {v('home_xg')} / Away xG {v('away_xg')}; Home xGA {v('home_xga')} / Away xGA {v('away_xga')}."),
        ("FBref team/match stats snapshot", f"Possession {v('home_possession')} - {v('away_possession')}; shots {v('home_shots')} - {v('away_shots')}."),
        ("Shot profile", f"Shots on target {v('home_shots_on_target')} - {v('away_shots_on_target')}."),
        ("Possession and passing profile", f"Pass completion {v('home_pass_completion_pct')} - {v('away_pass_completion_pct')}."),
        ("Progression profile", f"Progressive passes {v('home_progressive_passes')} - {v('away_progressive_passes')}; carries {v('home_progressive_carries')} - {v('away_progressive_carries')}."),
        ("Defensive actions profile", f"Tackles {v('home_tackles')} - {v('away_tackles')}; interceptions {v('home_interceptions')} - {v('away_interceptions')}; blocks {v('home_blocks')} - {v('away_blocks')}; clearances {v('home_clearances')} - {v('away_clearances')}."),
        ("Data gaps / missing optional fields", v("missing_optional_fields")),
        ("Preview-only model safety note", "Preview only. No production model prediction logic is called or activated."),
        ("No betting/staking note", "No betting tips, staking instructions, ROI logic, or stake sizing are generated."),
        ("Recommendation", CONTEXT_ENRICHED_HUMAN_REPORT_PREVIEW_READY),
    ]
    markdown = ["# Context-Enriched Human Match Report Preview", ""]
    for title, body in sections:
        markdown.extend([f"## {title}", "", body, ""])
    return "\n".join(markdown), len(sections)


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "context_enriched_human_report").resolve()
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


def _notes(missing_optional: int) -> str:
    notes = [CONTEXT_ENRICHED_HUMAN_REPORT_NETWORK_DISABLED_BY_DESIGN]
    if missing_optional:
        notes.append(CONTEXT_ENRICHED_HUMAN_REPORT_OPTIONAL_VALUES_MISSING)
    notes.extend([CONTEXT_ENRICHED_HUMAN_REPORT_NO_MODEL_INTEGRATION_BY_DESIGN, CONTEXT_ENRICHED_HUMAN_REPORT_NO_BETTING_INTEGRATION_BY_DESIGN])
    return "; ".join(notes)
