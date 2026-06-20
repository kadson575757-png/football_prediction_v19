# -*- coding: utf-8 -*-
"""Single-match analysis report preview builder."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.input_bundle import REQUIRED_CANONICAL_MATCH_FIELDS

SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW_READY = "SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW_READY"
SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_INPUT_BUNDLE = "SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_INPUT_BUNDLE"
SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_REQUIRED_COLUMNS = "SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_REQUIRED_COLUMNS"
SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_REQUIRED_VALUES = "SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_REQUIRED_VALUES"
SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_MATCH_NOT_FOUND = "SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_MATCH_NOT_FOUND"
SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_UNSAFE_PATH = "SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_UNSAFE_PATH"
SINGLE_MATCH_ANALYSIS_REPORT_MODEL_DISABLED_BY_DESIGN = "SINGLE_MATCH_ANALYSIS_REPORT_MODEL_DISABLED_BY_DESIGN"
SINGLE_MATCH_ANALYSIS_REPORT_BETTING_DISABLED_BY_DESIGN = "SINGLE_MATCH_ANALYSIS_REPORT_BETTING_DISABLED_BY_DESIGN"

MANIFEST_COLUMNS = [
    "report_id",
    "source_id",
    "provider_match_id",
    "league",
    "season",
    "input_path",
    "report_path",
    "summary_path",
    "rows_input",
    "rows_reported",
    "missing_required_columns",
    "missing_required_values",
    "network_calls_enabled",
    "prediction_logic_enabled",
    "betting_logic_enabled",
    "report_status",
    "recommendation",
    "notes",
]


@dataclass(frozen=True)
class SingleMatchAnalysisReportConfig:
    input_path: str | Path | None = None
    match_id: str | None = None
    output_dir: str | Path = "outputs/analysis_preview/single_match_report"
    write_preview: bool = False
    base_dir: str | Path = "."
    report_id: str = "single_match_analysis_report_preview"


@dataclass(frozen=True)
class SingleMatchAnalysisReportResult:
    report_id: str
    source_id: str
    provider_match_id: str
    league: str
    season: str
    input_path: str
    report_path: str
    summary_path: str
    rows_input: int
    rows_reported: int
    missing_required_columns: str
    missing_required_values: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    report_status: str
    recommendation: str
    notes: str


class SingleMatchAnalysisReportBuilder:
    def __init__(self, config: SingleMatchAnalysisReportConfig) -> None:
        self.config = config

    def build(self) -> tuple[SingleMatchAnalysisReportResult, pd.DataFrame, str]:
        cfg = self.config
        base = Path(cfg.base_dir).resolve()
        out_dir = _safe_output_dir(cfg.output_dir, base)
        if out_dir is None:
            result = _result(cfg, SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_UNSAFE_PATH, "OUTPUT_DIR_MUST_BE_UNDER_OUTPUTS_ANALYSIS_PREVIEW_SINGLE_MATCH_REPORT")
            return result, pd.DataFrame(), build_markdown_report(result, pd.Series(dtype=object), pd.DataFrame())

        input_path = Path(cfg.input_path) if cfg.input_path is not None else base / "outputs" / "analysis_preview" / "input_bundle" / "canonical_match_analysis_input_preview.csv"
        if not input_path.is_absolute():
            input_path = base / input_path
        if not input_path.exists():
            result = _result(cfg, SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_INPUT_BUNDLE, "INPUT_BUNDLE_NOT_FOUND", input_path=input_path)
            return result, pd.DataFrame(), build_markdown_report(result, pd.Series(dtype=object), pd.DataFrame())

        try:
            frame = pd.read_csv(input_path, low_memory=False)
        except Exception as exc:
            result = _result(cfg, SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_INPUT_BUNDLE, f"INPUT_BUNDLE_READ_FAILED:{exc}", input_path=input_path)
            return result, pd.DataFrame(), build_markdown_report(result, pd.Series(dtype=object), pd.DataFrame())

        missing_columns = [column for column in REQUIRED_CANONICAL_MATCH_FIELDS if column not in frame.columns]
        if missing_columns:
            result = _result(
                cfg,
                SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_REQUIRED_COLUMNS,
                "MISSING_REQUIRED_COLUMNS",
                input_path=input_path,
                rows_input=len(frame),
                missing_required_columns=" | ".join(missing_columns),
            )
            return result, pd.DataFrame(), build_markdown_report(result, pd.Series(dtype=object), frame)

        missing_values = _missing_required_values(frame)
        if missing_values:
            result = _result(
                cfg,
                SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_REQUIRED_VALUES,
                "MISSING_REQUIRED_VALUES",
                input_path=input_path,
                rows_input=len(frame),
                missing_required_values=" | ".join(missing_values),
            )
            return result, pd.DataFrame(), build_markdown_report(result, pd.Series(dtype=object), frame)

        if cfg.match_id:
            selected = frame[frame["provider_match_id"].astype(str).eq(str(cfg.match_id))]
            if selected.empty:
                result = _result(cfg, SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_MATCH_NOT_FOUND, "MATCH_ID_NOT_FOUND", input_path=input_path, rows_input=len(frame))
                return result, pd.DataFrame(), build_markdown_report(result, pd.Series(dtype=object), frame)
            match = selected.iloc[0]
        else:
            match = frame.iloc[0]

        summary = pd.DataFrame([{
            "source_id": match["source_id"],
            "provider_match_id": match["provider_match_id"],
            "league": match["league"],
            "season": match["season"],
            "date": match["date"],
            "home_team": match["home_team"],
            "away_team": match["away_team"],
            "home_goals": match["home_goals"],
            "away_goals": match["away_goals"],
            "match_status": match["match_status"],
            "network_calls_enabled": False,
            "prediction_logic_enabled": False,
            "betting_logic_enabled": False,
        }])
        report_path = ""
        summary_path = ""
        result = SingleMatchAnalysisReportResult(
            report_id=cfg.report_id,
            source_id=str(match["source_id"]),
            provider_match_id=str(match["provider_match_id"]),
            league=str(match["league"]),
            season=str(match["season"]),
            input_path=str(input_path.resolve()),
            report_path="",
            summary_path="",
            rows_input=int(len(frame)),
            rows_reported=1,
            missing_required_columns="",
            missing_required_values="",
            network_calls_enabled=False,
            prediction_logic_enabled=False,
            betting_logic_enabled=False,
            report_status=SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW_READY,
            recommendation=SINGLE_MATCH_ANALYSIS_REPORT_PREVIEW_READY,
            notes=f"{SINGLE_MATCH_ANALYSIS_REPORT_MODEL_DISABLED_BY_DESIGN}; {SINGLE_MATCH_ANALYSIS_REPORT_BETTING_DISABLED_BY_DESIGN}",
        )
        markdown = build_markdown_report(result, match, frame)
        if cfg.write_preview:
            out_dir.mkdir(parents=True, exist_ok=True)
            report_file = (out_dir / "single_match_analysis_report_preview.md").resolve()
            summary_file = (out_dir / "single_match_analysis_report_summary.csv").resolve()
            if not _is_under(report_file, out_dir) or not _is_under(summary_file, out_dir):
                blocked = _result(cfg, SINGLE_MATCH_ANALYSIS_REPORT_BLOCKED_UNSAFE_PATH, "REPORT_OUTPUT_OUTSIDE_PREVIEW_DIR", input_path=input_path, rows_input=len(frame))
                return blocked, pd.DataFrame(), build_markdown_report(blocked, pd.Series(dtype=object), frame)
            report_file.write_text(markdown, encoding="utf-8")
            summary.to_csv(summary_file, index=False)
            report_path = str(report_file)
            summary_path = str(summary_file)
            result = SingleMatchAnalysisReportResult(**{**result.__dict__, "report_path": report_path, "summary_path": summary_path})
        return result, summary, markdown


def build_manifest_frame(result: SingleMatchAnalysisReportResult) -> pd.DataFrame:
    return pd.DataFrame([result.__dict__], columns=MANIFEST_COLUMNS)


def build_markdown_report(result: SingleMatchAnalysisReportResult, match: pd.Series, frame: pd.DataFrame) -> str:
    has_match = not match.empty
    available = list(frame.columns) if not frame.empty else []
    warnings = result.missing_required_columns or result.missing_required_values or "None for selected preview row."
    return "\n".join([
        "# Analysis Report Preview Header",
        "",
        "This is a preview-only analysis report. No model prediction was run. No betting/staking recommendation was generated. No live external data was fetched.",
        "",
        "## Match Identity",
        f"- provider_match_id: {result.provider_match_id if has_match else ''}",
        f"- match: {match.get('home_team', '') if has_match else ''} vs {match.get('away_team', '') if has_match else ''}",
        f"- league: {result.league}",
        f"- season: {result.season}",
        f"- date: {match.get('date', '') if has_match else ''}",
        "",
        "## Data Source / Contract",
        f"- source_id: {result.source_id}",
        "- contract: canonical_match",
        f"- input_path: {result.input_path}",
        "",
        "## Input Bundle Validation",
        f"- rows_input: {result.rows_input}",
        f"- rows_reported: {result.rows_reported}",
        f"- status: {result.report_status}",
        "",
        "## Score / Match Status",
        f"- score: {match.get('home_goals', '') if has_match else ''}-{match.get('away_goals', '') if has_match else ''}",
        f"- match_status: {match.get('match_status', '') if has_match else ''}",
        "",
        "## Available Canonical Fields",
        ", ".join(available),
        "",
        "## Missing Data Warnings",
        warnings,
        "",
        "## Prediction Logic Status",
        "prediction_logic_enabled=false; no model prediction was run.",
        "",
        "## Betting Logic Status",
        "betting_logic_enabled=false; no betting/staking recommendation was generated.",
        "",
        "## Network / Scraping Status",
        "network_calls_enabled=false; no live external data was fetched.",
        "",
        "## Safety Notes",
        "Imported/local values are not yet integrated into production model logic. No probability, market, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "",
        "## Recommendation",
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
    allowed = (base_dir / "outputs" / "analysis_preview" / "single_match_report").resolve()
    if resolved == allowed or allowed in resolved.parents:
        return resolved
    return None


def _is_under(path: Path, parent: Path) -> bool:
    resolved = path.resolve()
    allowed = parent.resolve()
    return resolved == allowed or allowed in resolved.parents


def _result(
    cfg: SingleMatchAnalysisReportConfig,
    status: str,
    notes: str,
    *,
    input_path: Path | None = None,
    rows_input: int = 0,
    missing_required_columns: str = "",
    missing_required_values: str = "",
) -> SingleMatchAnalysisReportResult:
    path_text = str(input_path.resolve()) if input_path else str(cfg.input_path or "")
    return SingleMatchAnalysisReportResult(
        report_id=cfg.report_id,
        source_id="",
        provider_match_id=str(cfg.match_id or ""),
        league="",
        season="",
        input_path=path_text,
        report_path="",
        summary_path="",
        rows_input=int(rows_input),
        rows_reported=0,
        missing_required_columns=missing_required_columns,
        missing_required_values=missing_required_values,
        network_calls_enabled=False,
        prediction_logic_enabled=False,
        betting_logic_enabled=False,
        report_status=status,
        recommendation=status,
        notes=notes,
    )

