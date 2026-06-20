# -*- coding: utf-8 -*-
"""Single-match context enrichment preview builder."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW_READY = "SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW_READY"
SINGLE_MATCH_CONTEXT_ENRICHMENT_PARTIAL_READY = "SINGLE_MATCH_CONTEXT_ENRICHMENT_PARTIAL_READY"
SINGLE_MATCH_CONTEXT_ENRICHMENT_BLOCKED_MISSING_BASE_REPORT = "SINGLE_MATCH_CONTEXT_ENRICHMENT_BLOCKED_MISSING_BASE_REPORT"
SINGLE_MATCH_CONTEXT_ENRICHMENT_BLOCKED_MISSING_REQUIRED_COLUMNS = "SINGLE_MATCH_CONTEXT_ENRICHMENT_BLOCKED_MISSING_REQUIRED_COLUMNS"
SINGLE_MATCH_CONTEXT_ENRICHMENT_BLOCKED_UNSAFE_PATH = "SINGLE_MATCH_CONTEXT_ENRICHMENT_BLOCKED_UNSAFE_PATH"
CONTEXT_AVAILABLE = "CONTEXT_AVAILABLE"
CONTEXT_OPTIONAL_MISSING = "CONTEXT_OPTIONAL_MISSING"
CONTEXT_NO_MATCH_FOR_SELECTED_MATCH = "CONTEXT_NO_MATCH_FOR_SELECTED_MATCH"
CONTEXT_NETWORK_DISABLED_BY_DESIGN = "CONTEXT_NETWORK_DISABLED_BY_DESIGN"
CONTEXT_MODEL_DISABLED_BY_DESIGN = "CONTEXT_MODEL_DISABLED_BY_DESIGN"
CONTEXT_BETTING_DISABLED_BY_DESIGN = "CONTEXT_BETTING_DISABLED_BY_DESIGN"

REQUIRED_BASE_COLUMNS = [
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
    "network_calls_enabled",
    "prediction_logic_enabled",
    "betting_logic_enabled",
    "report_status",
    "recommendation",
]

MANIFEST_COLUMNS = [
    "enrichment_id",
    "source_id",
    "provider_match_id",
    "league",
    "season",
    "base_report_manifest_path",
    "output_report_path",
    "output_summary_path",
    "rows_reported",
    "contexts_checked",
    "contexts_available",
    "contexts_missing_optional",
    "network_calls_enabled",
    "prediction_logic_enabled",
    "betting_logic_enabled",
    "enrichment_status",
    "recommendation",
    "notes",
]

SUMMARY_COLUMNS = [
    "context_name",
    "context_status",
    "input_path",
    "rows_available",
    "rows_matched",
    "warning",
    "recommendation",
]

OPTIONAL_CONTEXTS = [
    ("analysis_input_bundle", "outputs/analysis_preview/input_bundle/canonical_match_analysis_input_preview.csv"),
    ("file_based_importer_canonical_match", "outputs/importer_preview/normalized/canonical_match_preview.csv"),
    ("xg_reporting_pack", "outputs/analysis_preview/xg_reporting_pack/xg_reporting_pack_preview.csv"),
    ("xg_matchup", "outputs/analysis_preview/xg_matchup/xg_matchup_preview.csv"),
    ("rolling_xg_form", "outputs/analysis_preview/rolling_xg_form/rolling_xg_form_preview.csv"),
    ("team_xg_aggregates", "outputs/analysis_preview/team_xg_aggregates/team_xg_aggregates_preview.csv"),
]


@dataclass(frozen=True)
class SingleMatchContextEnrichmentConfig:
    base_report_manifest_path: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/single_match_context"
    write_preview: bool = False
    base_dir: str | Path = "."
    enrichment_id: str = "single_match_context_enrichment_preview"


@dataclass(frozen=True)
class SingleMatchContextEnrichmentResult:
    enrichment_id: str
    source_id: str
    provider_match_id: str
    league: str
    season: str
    base_report_manifest_path: str
    output_report_path: str
    output_summary_path: str
    rows_reported: int
    contexts_checked: int
    contexts_available: int
    contexts_missing_optional: int
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    enrichment_status: str
    recommendation: str
    notes: str


class SingleMatchContextEnrichmentBuilder:
    def __init__(self, config: SingleMatchContextEnrichmentConfig) -> None:
        self.config = config

    def build(self) -> tuple[SingleMatchContextEnrichmentResult, pd.DataFrame, str]:
        cfg = self.config
        base = Path(cfg.base_dir).resolve()
        out_dir = _safe_output_dir(cfg.output_dir, base)
        if out_dir is None:
            result = _result(cfg, SINGLE_MATCH_CONTEXT_ENRICHMENT_BLOCKED_UNSAFE_PATH, "OUTPUT_DIR_MUST_BE_UNDER_OUTPUTS_ANALYSIS_PREVIEW_SINGLE_MATCH_CONTEXT")
            return result, pd.DataFrame(columns=SUMMARY_COLUMNS), build_markdown(result, pd.DataFrame(columns=SUMMARY_COLUMNS))

        manifest = Path(cfg.base_report_manifest_path) if cfg.base_report_manifest_path is not None else base / "outputs" / "analysis_preview" / "single_match_report" / "single_match_analysis_report_manifest.csv"
        if not manifest.is_absolute():
            manifest = base / manifest
        if not manifest.exists():
            result = _result(cfg, SINGLE_MATCH_CONTEXT_ENRICHMENT_BLOCKED_MISSING_BASE_REPORT, "BASE_REPORT_MANIFEST_NOT_FOUND", manifest_path=manifest)
            return result, pd.DataFrame(columns=SUMMARY_COLUMNS), build_markdown(result, pd.DataFrame(columns=SUMMARY_COLUMNS))

        try:
            base_manifest = pd.read_csv(manifest, low_memory=False)
        except Exception as exc:
            result = _result(cfg, SINGLE_MATCH_CONTEXT_ENRICHMENT_BLOCKED_MISSING_BASE_REPORT, f"BASE_REPORT_READ_FAILED:{exc}", manifest_path=manifest)
            return result, pd.DataFrame(columns=SUMMARY_COLUMNS), build_markdown(result, pd.DataFrame(columns=SUMMARY_COLUMNS))

        missing = [column for column in REQUIRED_BASE_COLUMNS if column not in base_manifest.columns]
        if missing:
            result = _result(
                cfg,
                SINGLE_MATCH_CONTEXT_ENRICHMENT_BLOCKED_MISSING_REQUIRED_COLUMNS,
                "MISSING_REQUIRED_COLUMNS",
                manifest_path=manifest,
                missing_columns=" | ".join(missing),
            )
            return result, pd.DataFrame(columns=SUMMARY_COLUMNS), build_markdown(result, pd.DataFrame(columns=SUMMARY_COLUMNS))

        row = base_manifest.iloc[0]
        summary = _context_summary(base, row)
        available = int(summary["context_status"].eq(CONTEXT_AVAILABLE).sum())
        missing_optional = int(summary["context_status"].eq(CONTEXT_OPTIONAL_MISSING).sum())
        result = SingleMatchContextEnrichmentResult(
            enrichment_id=cfg.enrichment_id,
            source_id=str(row["source_id"]),
            provider_match_id=str(row["provider_match_id"]),
            league=str(row["league"]),
            season=str(row["season"]),
            base_report_manifest_path=str(manifest.resolve()),
            output_report_path="",
            output_summary_path="",
            rows_reported=int(row["rows_reported"]),
            contexts_checked=int(len(summary)),
            contexts_available=available,
            contexts_missing_optional=missing_optional,
            network_calls_enabled=False,
            prediction_logic_enabled=False,
            betting_logic_enabled=False,
            enrichment_status=SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW_READY,
            recommendation=SINGLE_MATCH_CONTEXT_ENRICHMENT_PREVIEW_READY,
            notes=f"{CONTEXT_NETWORK_DISABLED_BY_DESIGN}; {CONTEXT_MODEL_DISABLED_BY_DESIGN}; {CONTEXT_BETTING_DISABLED_BY_DESIGN}",
        )
        markdown = build_markdown(result, summary)
        if cfg.write_preview:
            out_dir.mkdir(parents=True, exist_ok=True)
            report_file = (out_dir / "single_match_context_enrichment_preview.md").resolve()
            summary_file = (out_dir / "single_match_context_enrichment_summary.csv").resolve()
            if not _is_under(report_file, out_dir) or not _is_under(summary_file, out_dir):
                blocked = _result(cfg, SINGLE_MATCH_CONTEXT_ENRICHMENT_BLOCKED_UNSAFE_PATH, "CONTEXT_OUTPUT_OUTSIDE_PREVIEW_DIR", manifest_path=manifest)
                return blocked, pd.DataFrame(columns=SUMMARY_COLUMNS), build_markdown(blocked, pd.DataFrame(columns=SUMMARY_COLUMNS))
            report_file.write_text(markdown, encoding="utf-8")
            summary.to_csv(summary_file, index=False)
            result = SingleMatchContextEnrichmentResult(**{**result.__dict__, "output_report_path": str(report_file), "output_summary_path": str(summary_file)})
            markdown = build_markdown(result, summary)
            report_file.write_text(markdown, encoding="utf-8")
        return result, summary, markdown


def build_manifest_frame(result: SingleMatchContextEnrichmentResult) -> pd.DataFrame:
    return pd.DataFrame([result.__dict__], columns=MANIFEST_COLUMNS)


def build_markdown(result: SingleMatchContextEnrichmentResult, summary: pd.DataFrame) -> str:
    def section(name: str) -> str:
        rows = summary[summary["context_name"].eq(name)] if not summary.empty else pd.DataFrame()
        if rows.empty:
            return "not checked"
        row = rows.iloc[0]
        return f"{row['context_status']} ({row['warning']})"

    warnings = summary[summary["context_status"].eq(CONTEXT_OPTIONAL_MISSING)] if not summary.empty else pd.DataFrame()
    warning_text = "None." if warnings.empty else "; ".join(warnings["context_name"].astype(str).tolist())
    return "\n".join([
        "# Context Enrichment Preview Header",
        "",
        "This is preview-only context enrichment. No model prediction was run. No betting/staking recommendation was generated. No live external data was fetched. Missing optional context is not inferred or invented.",
        "",
        "## Match Identity",
        f"- provider_match_id: {result.provider_match_id}",
        f"- source_id: {result.source_id}",
        f"- league: {result.league}",
        f"- season: {result.season}",
        "",
        "## Base Single-Match Report Status",
        f"- rows_reported: {result.rows_reported}",
        f"- base_report_manifest_path: {result.base_report_manifest_path}",
        "",
        "## Analysis Input Bundle Status",
        section("analysis_input_bundle"),
        "",
        "## Importer / Canonical Match Context",
        section("file_based_importer_canonical_match"),
        "",
        "## xG Reporting Pack Context",
        section("xg_reporting_pack"),
        "",
        "## Team xG Aggregate Context",
        section("team_xg_aggregates"),
        "",
        "## Rolling xG Form Context",
        section("rolling_xg_form"),
        "",
        "## xG Matchup Context",
        section("xg_matchup"),
        "",
        "## Missing Optional Context Warnings",
        warning_text,
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
        "Imported/local values are not yet integrated into production model logic. Optional context values are reported only when local files exist; missing context is not inferred or invented.",
        "",
        "## Recommendation",
        result.recommendation,
        "",
    ])


def _context_summary(base: Path, match: pd.Series) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    provider_match_id = str(match["provider_match_id"])
    for name, rel_path in OPTIONAL_CONTEXTS:
        path = base / rel_path
        if not path.exists():
            rows.append(_context_row(name, CONTEXT_OPTIONAL_MISSING, path, 0, 0, "Optional local context file missing."))
            continue
        try:
            frame = pd.read_csv(path, low_memory=False)
        except Exception as exc:
            rows.append(_context_row(name, CONTEXT_OPTIONAL_MISSING, path, 0, 0, f"Optional context unreadable: {exc}"))
            continue
        matched = _rows_matched(frame, provider_match_id)
        status = CONTEXT_AVAILABLE if matched > 0 or name in {"analysis_input_bundle", "file_based_importer_canonical_match"} else CONTEXT_NO_MATCH_FOR_SELECTED_MATCH
        warning = "" if status == CONTEXT_AVAILABLE else "Local context file exists but no selected-match row was found."
        rows.append(_context_row(name, status, path, len(frame), matched, warning))
    return pd.DataFrame(rows, columns=SUMMARY_COLUMNS)


def _rows_matched(frame: pd.DataFrame, provider_match_id: str) -> int:
    if "provider_match_id" in frame.columns:
        return int(frame["provider_match_id"].astype(str).eq(provider_match_id).sum())
    return int(len(frame))


def _context_row(name: str, status: str, path: Path, rows_available: int, rows_matched: int, warning: str) -> dict[str, object]:
    return {
        "context_name": name,
        "context_status": status,
        "input_path": str(path),
        "rows_available": int(rows_available),
        "rows_matched": int(rows_matched),
        "warning": warning,
        "recommendation": status,
    }


def _safe_output_dir(output_dir: str | Path, base_dir: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base_dir / out
    resolved = out.resolve()
    allowed = (base_dir / "outputs" / "analysis_preview" / "single_match_context").resolve()
    if resolved == allowed or allowed in resolved.parents:
        return resolved
    return None


def _is_under(path: Path, parent: Path) -> bool:
    resolved = path.resolve()
    allowed = parent.resolve()
    return resolved == allowed or allowed in resolved.parents


def _result(
    cfg: SingleMatchContextEnrichmentConfig,
    status: str,
    notes: str,
    *,
    manifest_path: Path | None = None,
    missing_columns: str = "",
) -> SingleMatchContextEnrichmentResult:
    return SingleMatchContextEnrichmentResult(
        enrichment_id=cfg.enrichment_id,
        source_id="",
        provider_match_id="",
        league="",
        season="",
        base_report_manifest_path=str(manifest_path.resolve()) if manifest_path else str(cfg.base_report_manifest_path or ""),
        output_report_path="",
        output_summary_path="",
        rows_reported=0,
        contexts_checked=0,
        contexts_available=0,
        contexts_missing_optional=0,
        network_calls_enabled=False,
        prediction_logic_enabled=False,
        betting_logic_enabled=False,
        enrichment_status=status,
        recommendation=status,
        notes=f"{notes}; {missing_columns}".strip("; "),
    )

