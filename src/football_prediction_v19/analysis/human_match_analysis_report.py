# -*- coding: utf-8 -*-
"""Human-facing single-match analysis report preview."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

HUMAN_MATCH_ANALYSIS_REPORT_PREVIEW_READY = "HUMAN_MATCH_ANALYSIS_REPORT_PREVIEW_READY"
HUMAN_MATCH_ANALYSIS_REPORT_PARTIAL_READY = "HUMAN_MATCH_ANALYSIS_REPORT_PARTIAL_READY"
HUMAN_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_CONTEXT = "HUMAN_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_CONTEXT"
HUMAN_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_REQUIRED_COLUMNS = "HUMAN_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_REQUIRED_COLUMNS"
HUMAN_MATCH_ANALYSIS_REPORT_BLOCKED_UNSAFE_PATH = "HUMAN_MATCH_ANALYSIS_REPORT_BLOCKED_UNSAFE_PATH"
HUMAN_MATCH_ANALYSIS_REPORT_MODEL_DISABLED_BY_DESIGN = "HUMAN_MATCH_ANALYSIS_REPORT_MODEL_DISABLED_BY_DESIGN"
HUMAN_MATCH_ANALYSIS_REPORT_BETTING_DISABLED_BY_DESIGN = "HUMAN_MATCH_ANALYSIS_REPORT_BETTING_DISABLED_BY_DESIGN"
HUMAN_MATCH_ANALYSIS_REPORT_CONTEXT_OPTIONAL_MISSING = "HUMAN_MATCH_ANALYSIS_REPORT_CONTEXT_OPTIONAL_MISSING"

REQUIRED_CONTEXT_COLUMNS = [
    "enrichment_id", "source_id", "provider_match_id", "league", "season",
    "base_report_manifest_path", "output_report_path", "output_summary_path",
    "rows_reported", "contexts_checked", "contexts_available",
    "contexts_missing_optional", "network_calls_enabled",
    "prediction_logic_enabled", "betting_logic_enabled", "enrichment_status",
    "recommendation", "notes",
]

MANIFEST_COLUMNS = [
    "human_report_id", "source_id", "provider_match_id", "league", "season",
    "context_manifest_path", "output_report_path", "output_summary_path",
    "rows_reported", "contexts_checked", "contexts_available",
    "contexts_missing_optional", "network_calls_enabled",
    "prediction_logic_enabled", "betting_logic_enabled", "human_report_status",
    "recommendation", "notes",
]

SUMMARY_COLUMNS = ["section_name", "section_status", "rows_available", "rows_used", "warning", "recommendation", "notes"]


@dataclass(frozen=True)
class HumanMatchAnalysisReportConfig:
    context_manifest_path: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/human_match_report"
    write_preview: bool = False
    base_dir: str | Path = "."
    human_report_id: str = "human_match_analysis_report_preview"


@dataclass(frozen=True)
class HumanMatchAnalysisReportResult:
    human_report_id: str
    source_id: str
    provider_match_id: str
    league: str
    season: str
    context_manifest_path: str
    output_report_path: str
    output_summary_path: str
    rows_reported: int
    contexts_checked: int
    contexts_available: int
    contexts_missing_optional: int
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    human_report_status: str
    recommendation: str
    notes: str


class HumanMatchAnalysisReportBuilder:
    def __init__(self, config: HumanMatchAnalysisReportConfig) -> None:
        self.config = config

    def build(self) -> tuple[HumanMatchAnalysisReportResult, pd.DataFrame, str]:
        cfg = self.config
        base = Path(cfg.base_dir).resolve()
        out_dir = _safe_output_dir(cfg.output_dir, base)
        if out_dir is None:
            result = _result(cfg, HUMAN_MATCH_ANALYSIS_REPORT_BLOCKED_UNSAFE_PATH, "OUTPUT_DIR_MUST_BE_UNDER_OUTPUTS_ANALYSIS_PREVIEW_HUMAN_MATCH_REPORT")
            return result, pd.DataFrame(columns=SUMMARY_COLUMNS), build_markdown(result, pd.DataFrame(columns=SUMMARY_COLUMNS))

        manifest = Path(cfg.context_manifest_path) if cfg.context_manifest_path is not None else base / "outputs" / "analysis_preview" / "single_match_context" / "single_match_context_enrichment_manifest.csv"
        if not manifest.is_absolute():
            manifest = base / manifest
        if not manifest.exists():
            result = _result(cfg, HUMAN_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_CONTEXT, "CONTEXT_MANIFEST_NOT_FOUND", manifest_path=manifest)
            return result, pd.DataFrame(columns=SUMMARY_COLUMNS), build_markdown(result, pd.DataFrame(columns=SUMMARY_COLUMNS))
        try:
            context = pd.read_csv(manifest, low_memory=False)
        except Exception as exc:
            result = _result(cfg, HUMAN_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_CONTEXT, f"CONTEXT_MANIFEST_READ_FAILED:{exc}", manifest_path=manifest)
            return result, pd.DataFrame(columns=SUMMARY_COLUMNS), build_markdown(result, pd.DataFrame(columns=SUMMARY_COLUMNS))
        missing = [column for column in REQUIRED_CONTEXT_COLUMNS if column not in context.columns]
        if missing:
            result = _result(cfg, HUMAN_MATCH_ANALYSIS_REPORT_BLOCKED_MISSING_REQUIRED_COLUMNS, "MISSING_REQUIRED_COLUMNS: " + " | ".join(missing), manifest_path=manifest)
            return result, pd.DataFrame(columns=SUMMARY_COLUMNS), build_markdown(result, pd.DataFrame(columns=SUMMARY_COLUMNS))
        row = context.iloc[0]
        summary = _summary_sections(row)
        result = HumanMatchAnalysisReportResult(
            human_report_id=cfg.human_report_id,
            source_id=str(row["source_id"]),
            provider_match_id=str(row["provider_match_id"]),
            league=str(row["league"]),
            season=str(row["season"]),
            context_manifest_path=str(manifest.resolve()),
            output_report_path="",
            output_summary_path="",
            rows_reported=int(row["rows_reported"]),
            contexts_checked=int(row["contexts_checked"]),
            contexts_available=int(row["contexts_available"]),
            contexts_missing_optional=int(row["contexts_missing_optional"]),
            network_calls_enabled=False,
            prediction_logic_enabled=False,
            betting_logic_enabled=False,
            human_report_status=HUMAN_MATCH_ANALYSIS_REPORT_PREVIEW_READY,
            recommendation=HUMAN_MATCH_ANALYSIS_REPORT_PREVIEW_READY,
            notes=f"{HUMAN_MATCH_ANALYSIS_REPORT_MODEL_DISABLED_BY_DESIGN}; {HUMAN_MATCH_ANALYSIS_REPORT_BETTING_DISABLED_BY_DESIGN}",
        )
        markdown = build_markdown(result, summary)
        if cfg.write_preview:
            out_dir.mkdir(parents=True, exist_ok=True)
            report_file = (out_dir / "human_match_analysis_report_preview.md").resolve()
            summary_file = (out_dir / "human_match_analysis_report_summary.csv").resolve()
            if not _is_under(report_file, out_dir) or not _is_under(summary_file, out_dir):
                blocked = _result(cfg, HUMAN_MATCH_ANALYSIS_REPORT_BLOCKED_UNSAFE_PATH, "HUMAN_REPORT_OUTPUT_OUTSIDE_PREVIEW_DIR", manifest_path=manifest)
                return blocked, pd.DataFrame(columns=SUMMARY_COLUMNS), build_markdown(blocked, pd.DataFrame(columns=SUMMARY_COLUMNS))
            summary.to_csv(summary_file, index=False)
            result = HumanMatchAnalysisReportResult(**{**result.__dict__, "output_report_path": str(report_file), "output_summary_path": str(summary_file)})
            markdown = build_markdown(result, summary)
            report_file.write_text(markdown, encoding="utf-8")
        return result, summary, markdown


def build_manifest_frame(result: HumanMatchAnalysisReportResult) -> pd.DataFrame:
    return pd.DataFrame([result.__dict__], columns=MANIFEST_COLUMNS)


def build_markdown(result: HumanMatchAnalysisReportResult, summary: pd.DataFrame) -> str:
    missing_note = "None." if result.contexts_missing_optional == 0 else f"{result.contexts_missing_optional} optional context layer(s) missing and reported, not inferred."
    return "\n".join([
        "# Human Match Analysis Preview Header",
        "",
        "This is a preview-only human-facing analysis report. No model prediction was run. No betting/staking recommendation was generated. No live external data was fetched. Missing optional context is not inferred or invented.",
        "",
        "## Match Identity",
        f"- provider_match_id: {result.provider_match_id}",
        f"- source_id: {result.source_id}",
        f"- league: {result.league}",
        f"- season: {result.season}",
        "",
        "## Data Quality / Source Status",
        f"- context manifest: {result.context_manifest_path}",
        f"- contexts checked: {result.contexts_checked}",
        f"- contexts available: {result.contexts_available}",
        "",
        "## Available Canonical Match Data",
        "Canonical match identity is available from the local preview pipeline when the context manifest is ready.",
        "",
        "## Context Availability Overview",
        _markdown_table(summary) if not summary.empty else "No context summary available.",
        "",
        "## Importer / File-Based Source Context",
        "Local file-based importer context is preview-only and separate from production model logic.",
        "",
        "## xG Reporting Context",
        "xG context is included only when local preview files exist; xG is not activated as model features.",
        "",
        "## Team xG Aggregate Context",
        "Team aggregate context is optional and may be missing.",
        "",
        "## Rolling xG Form Context",
        "Rolling xG form context is optional and may be missing.",
        "",
        "## xG Matchup Context",
        "xG matchup context is optional and may be missing.",
        "",
        "## Missing Context Warnings",
        missing_note,
        "",
        "## Prediction Logic Status",
        "prediction_logic_enabled=false; no model prediction was run.",
        "",
        "## Betting / Staking Logic Status",
        "betting_logic_enabled=false; no betting/staking recommendation was generated.",
        "",
        "## No-Bet / Disabled Tips Notice",
        "No betting tips, staking advice, ROI logic, or active recommendations are generated in this preview.",
        "",
        "## Safety Notes",
        "Imported/local values are not yet integrated into production model logic. No probability, market, recommended-market, betting, staking, ROI, SUPER_A_TIER, or stake sizing logic changed.",
        "",
        "## Human Review Recommendation",
        "Review available local context and missing optional context before any future integration phase.",
        "",
        "## Next-Step Recommendation",
        result.recommendation,
        "",
    ])


def _summary_sections(row: pd.Series) -> pd.DataFrame:
    missing = int(row["contexts_missing_optional"])
    return pd.DataFrame([
        {"section_name": "context_manifest", "section_status": "CONTEXT_READY", "rows_available": int(row["contexts_checked"]), "rows_used": int(row["contexts_available"]), "warning": "", "recommendation": "USE_FOR_PREVIEW_ONLY", "notes": "Local context metadata only."},
        {"section_name": "missing_optional_context", "section_status": HUMAN_MATCH_ANALYSIS_REPORT_CONTEXT_OPTIONAL_MISSING if missing else "CONTEXT_COMPLETE", "rows_available": missing, "rows_used": 0, "warning": "Missing optional context is not inferred or invented." if missing else "", "recommendation": "REPORT_WARNING_ONLY", "notes": "Does not block preview."},
        {"section_name": "prediction_logic", "section_status": HUMAN_MATCH_ANALYSIS_REPORT_MODEL_DISABLED_BY_DESIGN, "rows_available": 0, "rows_used": 0, "warning": "", "recommendation": "DISABLED_BY_DESIGN", "notes": "No model prediction was run."},
        {"section_name": "betting_logic", "section_status": HUMAN_MATCH_ANALYSIS_REPORT_BETTING_DISABLED_BY_DESIGN, "rows_available": 0, "rows_used": 0, "warning": "", "recommendation": "DISABLED_BY_DESIGN", "notes": "No betting/staking recommendation was generated."},
    ], columns=SUMMARY_COLUMNS)


def _markdown_table(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame.iterrows():
        values = [str(row[column]).replace("|", ";") for column in columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _safe_output_dir(output_dir: str | Path, base_dir: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base_dir / out
    resolved = out.resolve()
    allowed = (base_dir / "outputs" / "analysis_preview" / "human_match_report").resolve()
    if resolved == allowed or allowed in resolved.parents:
        return resolved
    return None


def _is_under(path: Path, parent: Path) -> bool:
    resolved = path.resolve()
    allowed = parent.resolve()
    return resolved == allowed or allowed in resolved.parents


def _result(cfg: HumanMatchAnalysisReportConfig, status: str, notes: str, *, manifest_path: Path | None = None) -> HumanMatchAnalysisReportResult:
    return HumanMatchAnalysisReportResult(
        human_report_id=cfg.human_report_id, source_id="", provider_match_id="", league="", season="",
        context_manifest_path=str(manifest_path.resolve()) if manifest_path else str(cfg.context_manifest_path or ""),
        output_report_path="", output_summary_path="", rows_reported=0, contexts_checked=0,
        contexts_available=0, contexts_missing_optional=0, network_calls_enabled=False,
        prediction_logic_enabled=False, betting_logic_enabled=False, human_report_status=status,
        recommendation=status, notes=notes,
    )
