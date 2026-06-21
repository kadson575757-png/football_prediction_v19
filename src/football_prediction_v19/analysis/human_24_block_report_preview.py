# -*- coding: utf-8 -*-
"""Render a preview-only 24-block human match report."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

HUMAN_24_BLOCK_MATCH_REPORT_PREVIEW_READY = "HUMAN_24_BLOCK_MATCH_REPORT_PREVIEW_READY"
HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_MISSING_INPUT = "HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_MISSING_INPUT"
HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_MISSING_REQUIRED_COLUMNS = "HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_MISSING_REQUIRED_COLUMNS"
HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_MISSING_REQUIRED_VALUES = "HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_MISSING_REQUIRED_VALUES"
HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_UNSAFE_PATH = "HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_UNSAFE_PATH"
HUMAN_24_BLOCK_MATCH_REPORT_OPTIONAL_VALUES_MISSING = "HUMAN_24_BLOCK_MATCH_REPORT_OPTIONAL_VALUES_MISSING"
HUMAN_24_BLOCK_MATCH_REPORT_NO_MODEL_INTEGRATION_BY_DESIGN = "HUMAN_24_BLOCK_MATCH_REPORT_NO_MODEL_INTEGRATION_BY_DESIGN"
HUMAN_24_BLOCK_MATCH_REPORT_NO_BETTING_INTEGRATION_BY_DESIGN = "HUMAN_24_BLOCK_MATCH_REPORT_NO_BETTING_INTEGRATION_BY_DESIGN"
HUMAN_24_BLOCK_MATCH_REPORT_NETWORK_DISABLED_BY_DESIGN = "HUMAN_24_BLOCK_MATCH_REPORT_NETWORK_DISABLED_BY_DESIGN"

REQUIRED_SECTIONS = [
    "Screen / Data Checklist", "Match Identity", "Data Quality", "Understat xG/xGA Snapshot",
    "FBref Team / Match Stats Snapshot", "Shot Profile", "Possession Profile", "Passing Profile",
    "Progression Profile", "Defensive Actions Profile", "Home / Away Split Status",
    "Player xG / xA Status", "Lineups Status", "Injuries / Suspensions Status",
    "Recent Form Status", "H2H Status", "Contradictions / Data Gaps",
    "v1.9 Model Synthesis Status", "Control Model Status", "Chaos Score Status",
    "Underdog Win Score Status", "No-Bet / Safety List", "Score Family Status",
    "Final Preview Conclusion",
]
MANIFEST_COLUMNS = [
    "human_24_block_report_run_id", "context_human_input_path", "report_output_path",
    "rows_input", "rows_reported", "sections_rendered", "required_sections_rendered",
    "missing_required_fields_count", "missing_optional_fields_count",
    "human_24_block_report_status", "recommendation", "notes", "network_calls_enabled",
    "prediction_logic_enabled", "betting_logic_enabled",
]
REQUIRED_COLUMNS = ["analysis_input_id", "match_date", "competition", "season", "home_team", "away_team", "understat_provider_match_id", "fbref_provider_match_id"]
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class Human24BlockReportConfig:
    context_human_input_path: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/human_24_block_report"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class Human24BlockReportResult:
    human_24_block_report_run_id: str
    context_human_input_path: str
    report_output_path: str
    manifest_path: str
    rows_input: int
    rows_reported: int
    sections_rendered: int
    required_sections_rendered: int
    missing_required_fields_count: int
    missing_optional_fields_count: int
    human_24_block_report_status: str
    recommendation: str
    notes: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool


class Human24BlockReportRenderer:
    def __init__(self, config: Human24BlockReportConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> tuple[Human24BlockReportResult, str]:
        out = _safe_output(self.config.output_dir, self.base)
        if out is None:
            return self._blocked(HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_UNSAFE_PATH), ""
        source = _resolve(self.config.context_human_input_path, self.base) or self.base / "outputs" / "analysis_preview" / "context_bundle_human_input" / "context_bundle_human_input.csv"
        if _unsafe(source):
            return self._blocked(HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_UNSAFE_PATH, source=source), ""
        if not source.exists():
            return self._blocked(HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_MISSING_INPUT, source=source), ""
        frame = pd.read_csv(source, low_memory=False)
        missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
        if missing_columns:
            return self._blocked(HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_MISSING_REQUIRED_COLUMNS, source=source, rows_input=len(frame), notes=" | ".join(missing_columns)), ""
        missing_required = _missing_value_count(frame, REQUIRED_COLUMNS)
        if missing_required or len(frame) != 1:
            return self._blocked(HUMAN_24_BLOCK_MATCH_REPORT_BLOCKED_MISSING_REQUIRED_VALUES, source=source, rows_input=len(frame), missing_required=missing_required), ""
        row = frame.iloc[0]
        missing_optional = len([p for p in str(row.get("missing_optional_fields", "")).split(" | ") if p])
        report = _render(row)
        rendered = sum(1 for section in REQUIRED_SECTIONS if f"## {section}" in report)
        out.mkdir(parents=True, exist_ok=True)
        report_path = out / "human_24_block_match_report_preview.md"
        manifest_path = out / "human_24_block_match_report_manifest.csv"
        report_path.write_text(report, encoding="utf-8")
        result = Human24BlockReportResult(
            human_24_block_report_run_id="human_24_block_report_preview",
            context_human_input_path=str(source.resolve()),
            report_output_path=str(report_path.resolve()),
            manifest_path=str(manifest_path.resolve()),
            rows_input=len(frame),
            rows_reported=1,
            sections_rendered=len(REQUIRED_SECTIONS),
            required_sections_rendered=rendered,
            missing_required_fields_count=0,
            missing_optional_fields_count=missing_optional,
            human_24_block_report_status=HUMAN_24_BLOCK_MATCH_REPORT_PREVIEW_READY,
            recommendation=HUMAN_24_BLOCK_MATCH_REPORT_PREVIEW_READY,
            notes=_notes(missing_optional),
            network_calls_enabled=False,
            prediction_logic_enabled=False,
            betting_logic_enabled=False,
        )
        pd.DataFrame([{column: getattr(result, column) for column in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest_path, index=False)
        return result, report

    def _blocked(self, status: str, *, source: Path | None = None, rows_input: int = 0, missing_required: int = 0, notes: str = "") -> Human24BlockReportResult:
        return Human24BlockReportResult("human_24_block_report_preview", str(source or self.config.context_human_input_path or ""), "", "", rows_input, 0, 0, 0, missing_required, 0, status, status, notes or _notes(0), False, False, False)


def _render(row: pd.Series) -> str:
    def v(column: str) -> str:
        value = row.get(column, "")
        if pd.isna(value) or str(value).strip() == "":
            return "not provided"
        return str(value)

    unavailable = "not available in this preview layer"
    not_executed = "not executed in this preview layer"
    bodies = {
        "Screen / Data Checklist": f"Local preview context loaded. Missing optional fields: {v('missing_optional_fields')}.",
        "Match Identity": f"{v('home_team')} vs {v('away_team')} on {v('match_date')} ({v('competition')} {v('season')}).",
        "Data Quality": f"Understat: {v('understat_data_quality_status')}; FBref: {v('fbref_data_quality_status')}; context: {v('context_data_quality_status')}.",
        "Understat xG/xGA Snapshot": f"Home xG {v('home_xg')} / Away xG {v('away_xg')}; Home xGA {v('home_xga')} / Away xGA {v('away_xga')}.",
        "FBref Team / Match Stats Snapshot": f"Possession {v('home_possession')} - {v('away_possession')}; shots {v('home_shots')} - {v('away_shots')}.",
        "Shot Profile": f"Shots on target {v('home_shots_on_target')} - {v('away_shots_on_target')}.",
        "Possession Profile": f"Possession split {v('home_possession')} - {v('away_possession')}.",
        "Passing Profile": f"Pass completion {v('home_pass_completion_pct')} - {v('away_pass_completion_pct')}.",
        "Progression Profile": f"Progressive passes {v('home_progressive_passes')} - {v('away_progressive_passes')}; carries {v('home_progressive_carries')} - {v('away_progressive_carries')}.",
        "Defensive Actions Profile": f"Tackles {v('home_tackles')} - {v('away_tackles')}; interceptions {v('home_interceptions')} - {v('away_interceptions')}; blocks {v('home_blocks')} - {v('away_blocks')}.",
        "Home / Away Split Status": unavailable,
        "Player xG / xA Status": unavailable,
        "Lineups Status": unavailable,
        "Injuries / Suspensions Status": unavailable,
        "Recent Form Status": unavailable,
        "H2H Status": unavailable,
        "Contradictions / Data Gaps": f"Preview gaps are surfaced, not filled: {v('missing_optional_fields')}.",
        "v1.9 Model Synthesis Status": not_executed,
        "Control Model Status": not_executed,
        "Chaos Score Status": not_executed,
        "Underdog Win Score Status": not_executed,
        "No-Bet / Safety List": "Betting output is disabled by design. No betting tips, staking, ROI, or stake sizing are generated.",
        "Score Family Status": not_executed,
        "Final Preview Conclusion": HUMAN_24_BLOCK_MATCH_REPORT_PREVIEW_READY,
    }
    lines = ["# 24-Block Human Match Report Preview", ""]
    for section in REQUIRED_SECTIONS:
        lines.extend([f"## {section}", "", bodies[section], ""])
    return "\n".join(lines)


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "human_24_block_report").resolve()
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
    notes = [HUMAN_24_BLOCK_MATCH_REPORT_NETWORK_DISABLED_BY_DESIGN]
    if missing_optional:
        notes.append(HUMAN_24_BLOCK_MATCH_REPORT_OPTIONAL_VALUES_MISSING)
    notes.extend([HUMAN_24_BLOCK_MATCH_REPORT_NO_MODEL_INTEGRATION_BY_DESIGN, HUMAN_24_BLOCK_MATCH_REPORT_NO_BETTING_INTEGRATION_BY_DESIGN])
    return "; ".join(notes)
