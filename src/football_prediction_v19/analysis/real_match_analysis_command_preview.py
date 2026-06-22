# -*- coding: utf-8 -*-
"""One-command preview orchestration for real-match analysis artifacts."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY = "REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY"
REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_UNKNOWN_MATCH = "REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_UNKNOWN_MATCH"
REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_AMBIGUOUS_MATCH = "REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_AMBIGUOUS_MATCH"
REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_CONTEXT_BUNDLE = "REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_CONTEXT_BUNDLE"
REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_CONTEXT_BRIDGE = "REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_CONTEXT_BRIDGE"
REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_DIAGNOSTIC_SYNTHESIS = "REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_DIAGNOSTIC_SYNTHESIS"
REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_GATE_MATRIX = "REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_GATE_MATRIX"
REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_REPORT = "REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_REPORT"
REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_EXPORT_BUNDLE = "REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_EXPORT_BUNDLE"
REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_EXCEL_EXPORT = "REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_EXCEL_EXPORT"
REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_UNSAFE_PATH = "REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_UNSAFE_PATH"
REAL_MATCH_ANALYSIS_COMMAND_NO_MODEL_INTEGRATION_BY_DESIGN = "REAL_MATCH_ANALYSIS_COMMAND_NO_MODEL_INTEGRATION_BY_DESIGN"
REAL_MATCH_ANALYSIS_COMMAND_NO_BETTING_INTEGRATION_BY_DESIGN = "REAL_MATCH_ANALYSIS_COMMAND_NO_BETTING_INTEGRATION_BY_DESIGN"
REAL_MATCH_ANALYSIS_COMMAND_NO_STAKING_INTEGRATION_BY_DESIGN = "REAL_MATCH_ANALYSIS_COMMAND_NO_STAKING_INTEGRATION_BY_DESIGN"
REAL_MATCH_ANALYSIS_COMMAND_NETWORK_DISABLED_BY_DESIGN = "REAL_MATCH_ANALYSIS_COMMAND_NETWORK_DISABLED_BY_DESIGN"

MANIFEST_COLUMNS = [
    "real_match_analysis_command_run_id", "match_date", "competition", "season",
    "home_team", "away_team", "understat_provider_match_id", "fbref_provider_match_id",
    "cross_provider_match_key", "match_context_bundle_status", "context_bridge_status",
    "v19_diagnostic_synthesis_status", "v19_diagnostic_gate_matrix_status",
    "odds_market_movement_input_status", "market_movement_diagnostic_status",
    "lineups_availability_input_status", "availability_diagnostic_status",
    "human_24_block_report_status", "export_bundle_status", "excel_export_status",
    "command_status", "rows_joined", "rows_written", "rows_diagnosed",
    "rows_reported", "gates_evaluated", "gates_blocked", "gates_disabled",
    "sections_rendered", "required_sections_rendered", "exported_files_count",
    "sheets_written", "workbook_file_exists", "human_report_path",
    "excel_workbook_path", "export_bundle_dir", "artifact_index_path",
    "recommendation", "notes", "network_calls_enabled", "prediction_logic_enabled",
    "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled",
]
ARTIFACT_COLUMNS = [
    "artifact_type", "artifact_status", "artifact_path", "exists", "preview_only",
    "safe_for_review", "notes",
]
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class RealMatchAnalysisCommandConfig:
    cross_provider_match_key: str | None = None
    understat_provider_match_id: str | None = None
    fbref_provider_match_id: str | None = None
    home_team: str | None = None
    away_team: str | None = None
    match_date: str | None = None
    competition: str | None = None
    season: str | None = None
    output_dir: str | Path = "outputs/analysis_preview/real_match_analysis_command"
    export_bundle_output_dir: str | Path | None = None
    excel_output_dir: str | Path | None = None
    workbook_filename: str = "match_analysis_preview_workbook.xlsx"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class RealMatchAnalysisCommandResult:
    real_match_analysis_command_run_id: str
    match_date: str
    competition: str
    season: str
    home_team: str
    away_team: str
    understat_provider_match_id: str
    fbref_provider_match_id: str
    cross_provider_match_key: str
    match_context_bundle_status: str
    context_bridge_status: str
    v19_diagnostic_synthesis_status: str
    v19_diagnostic_gate_matrix_status: str
    odds_market_movement_input_status: str
    market_movement_diagnostic_status: str
    lineups_availability_input_status: str
    availability_diagnostic_status: str
    human_24_block_report_status: str
    export_bundle_status: str
    excel_export_status: str
    command_status: str
    rows_joined: int
    rows_written: int
    rows_diagnosed: int
    rows_reported: int
    gates_evaluated: int
    gates_blocked: int
    gates_disabled: int
    sections_rendered: int
    required_sections_rendered: int
    exported_files_count: int
    sheets_written: int
    workbook_file_exists: bool
    human_report_path: str
    excel_workbook_path: str
    export_bundle_dir: str
    artifact_index_path: str
    manifest_path: str
    summary_path: str
    recommendation: str
    notes: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool


class RealMatchAnalysisCommandRunner:
    def __init__(self, config: RealMatchAnalysisCommandConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> RealMatchAnalysisCommandResult:
        out = _safe_output(self.config.output_dir, self.base)
        bundle_out = _safe_export_dir(self.config.export_bundle_output_dir, self.base)
        excel_out = _safe_excel_dir(self.config.excel_output_dir, self.base)
        if out is None or bundle_out is None or excel_out is None:
            return self._blocked(REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_UNSAFE_PATH)
        from scripts.build_match_analysis_excel_export_preview import build_match_analysis_excel_export_preview
        from scripts.build_match_analysis_export_bundle_preview import build_match_analysis_export_bundle_preview
        from scripts.build_match_analysis_runner_preview import build_match_analysis_runner_preview

        key = self.config.cross_provider_match_key or ("u-bundesliga-2024-001" if not _has_selector(self.config) else None)
        runner = build_match_analysis_runner_preview(
            cross_provider_match_key=key,
            understat_provider_match_id=self.config.understat_provider_match_id,
            fbref_provider_match_id=self.config.fbref_provider_match_id,
            home_team=self.config.home_team,
            away_team=self.config.away_team,
            match_date=self.config.match_date,
            competition=self.config.competition,
            season=self.config.season,
            output_dir=self.base / "outputs" / "analysis_preview" / "match_analysis_runner",
            base_dir=self.base,
        )
        blocked = _blocked_from_runner(runner)
        if blocked:
            return self._blocked(blocked, runner=runner)
        bundle = build_match_analysis_export_bundle_preview(
            cross_provider_match_key=key,
            understat_provider_match_id=self.config.understat_provider_match_id,
            fbref_provider_match_id=self.config.fbref_provider_match_id,
            home_team=self.config.home_team,
            away_team=self.config.away_team,
            match_date=self.config.match_date,
            competition=self.config.competition,
            season=self.config.season,
            output_dir=bundle_out,
            base_dir=self.base,
        )
        if bundle.get("export_bundle_status") != "MATCH_ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY":
            return self._blocked(_blocked_from_export(bundle), runner=runner, bundle=bundle)
        excel = build_match_analysis_excel_export_preview(
            export_bundle_dir=bundle.get("export_bundle_dir"),
            output_dir=excel_out,
            workbook_filename=self.config.workbook_filename,
            base_dir=self.base,
        )
        if excel.get("excel_export_status") != "MATCH_ANALYSIS_EXCEL_EXPORT_PREVIEW_READY":
            return self._blocked(REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_EXCEL_EXPORT, runner=runner, bundle=bundle, excel=excel)

        out.mkdir(parents=True, exist_ok=True)
        manifest_path = out / "real_match_analysis_command_manifest.csv"
        summary_path = out / "real_match_analysis_command_summary.md"
        artifact_index_path = out / "real_match_analysis_artifact_index.csv"
        artifact_index_md_path = out / "real_match_analysis_artifact_index.md"
        result = RealMatchAnalysisCommandResult(
            "real_match_analysis_command_preview",
            str(runner.get("match_date", "")), str(runner.get("competition", "")),
            str(runner.get("season", "")), str(runner.get("home_team", "")),
            str(runner.get("away_team", "")), str(runner.get("understat_provider_match_id", "")),
            str(runner.get("fbref_provider_match_id", "")), str(runner.get("cross_provider_match_key", "")),
            str(runner.get("match_context_bundle_status", "")), str(runner.get("context_bridge_status", "")),
            str(runner.get("v19_diagnostic_synthesis_status", "")), str(runner.get("v19_diagnostic_gate_matrix_status", "")),
            str(runner.get("odds_market_movement_input_status", "")), str(runner.get("market_movement_diagnostic_status", "")),
            str(runner.get("lineups_availability_input_status", "")), str(runner.get("availability_diagnostic_status", "")),
            str(runner.get("human_24_block_report_status", "")), str(bundle.get("export_bundle_status", "")),
            str(excel.get("excel_export_status", "")), REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY,
            int(runner.get("rows_joined", 0) or 0), int(runner.get("rows_written", 0) or 0),
            1, int(runner.get("rows_reported", 0) or 0), int(runner.get("gates_evaluated", 0) or 0),
            int(runner.get("gates_blocked", 0) or 0), int(runner.get("gates_disabled", 0) or 0),
            int(runner.get("sections_rendered", 0) or 0), int(bundle.get("required_sections_rendered", 0) or 0),
            int(bundle.get("exported_files_count", 0) or 0), int(excel.get("sheets_written", 0) or 0),
            bool(excel.get("workbook_file_exists", False)), str(runner.get("report_output_path", "")),
            str(excel.get("workbook_output_path", "")), str(bundle.get("export_bundle_dir", "")),
            str(artifact_index_path.resolve()), str(manifest_path.resolve()), str(summary_path.resolve()),
            REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY, _notes(), False, False, False, False, False,
        )
        pd.DataFrame([{c: getattr(result, c) for c in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest_path, index=False)
        summary_path.write_text(_summary(result), encoding="utf-8")
        artifacts = _artifact_rows(out, runner, bundle, excel, manifest_path, summary_path)
        artifacts.to_csv(artifact_index_path, index=False)
        artifact_index_md_path.write_text(_artifact_markdown(artifacts), encoding="utf-8")
        return result

    def _blocked(self, status: str, *, runner: dict[str, object] | None = None, bundle: dict[str, object] | None = None, excel: dict[str, object] | None = None) -> RealMatchAnalysisCommandResult:
        runner = runner or {}
        bundle = bundle or {}
        excel = excel or {}
        return RealMatchAnalysisCommandResult(
            "real_match_analysis_command_preview", str(runner.get("match_date", "")),
            str(runner.get("competition", "")), str(runner.get("season", "")),
            str(runner.get("home_team", "")), str(runner.get("away_team", "")),
            str(runner.get("understat_provider_match_id", "")), str(runner.get("fbref_provider_match_id", "")),
            str(runner.get("cross_provider_match_key", "")), str(runner.get("match_context_bundle_status", "")),
            str(runner.get("context_bridge_status", "")), str(runner.get("v19_diagnostic_synthesis_status", "")),
            str(runner.get("v19_diagnostic_gate_matrix_status", "")), str(runner.get("odds_market_movement_input_status", "")),
            str(runner.get("market_movement_diagnostic_status", "")), str(runner.get("lineups_availability_input_status", "")),
            str(runner.get("availability_diagnostic_status", "")), str(runner.get("human_24_block_report_status", "")),
            str(bundle.get("export_bundle_status", "")), str(excel.get("excel_export_status", "")),
            status, int(runner.get("rows_joined", 0) or 0), int(runner.get("rows_written", 0) or 0),
            0, int(runner.get("rows_reported", 0) or 0), int(runner.get("gates_evaluated", 0) or 0),
            int(runner.get("gates_blocked", 0) or 0), int(runner.get("gates_disabled", 0) or 0),
            int(runner.get("sections_rendered", 0) or 0), int(bundle.get("required_sections_rendered", 0) or 0),
            int(bundle.get("exported_files_count", 0) or 0), int(excel.get("sheets_written", 0) or 0),
            bool(excel.get("workbook_file_exists", False)), str(runner.get("report_output_path", "")),
            str(excel.get("workbook_output_path", "")), str(bundle.get("export_bundle_dir", "")),
            "", "", "", status, _notes(), False, False, False, False, False,
        )


def _artifact_rows(out: Path, runner: dict[str, object], bundle: dict[str, object], excel: dict[str, object], manifest_path: Path, summary_path: Path) -> pd.DataFrame:
    rows = [
        ("match_context_bundle", runner.get("match_context_bundle_status", ""), out.parents[0] / "match_context_bundle" / "match_context_bundle.csv"),
        ("context_human_input", runner.get("context_bridge_status", ""), out.parents[0] / "context_bundle_human_input" / "context_bundle_human_input.csv"),
        ("v19_diagnostic_synthesis", runner.get("v19_diagnostic_synthesis_status", ""), out.parents[0] / "v19_diagnostic_synthesis" / "v19_diagnostic_synthesis.csv"),
        ("v19_diagnostic_gate_matrix", runner.get("v19_diagnostic_gate_matrix_status", ""), out.parents[0] / "v19_diagnostic_gate_matrix" / "v19_diagnostic_gate_matrix.csv"),
        ("odds_market_movement_input", runner.get("odds_market_movement_input_status", ""), out.parents[0] / "odds_market_movement_input" / "odds_market_movement_input.csv"),
        ("market_movement_diagnostic", runner.get("market_movement_diagnostic_status", ""), out.parents[0] / "market_movement_diagnostic" / "market_movement_diagnostic.csv"),
        ("lineups_availability_input", runner.get("lineups_availability_input_status", ""), out.parents[0] / "lineups_availability_input" / "lineups_availability_input.csv"),
        ("availability_diagnostic", runner.get("availability_diagnostic_status", ""), out.parents[0] / "availability_diagnostic" / "availability_diagnostic.csv"),
        ("human_24_block_report", runner.get("human_24_block_report_status", ""), runner.get("report_output_path", "")),
        ("export_bundle_manifest", bundle.get("export_bundle_status", ""), Path(str(bundle.get("manifest_path", "")))),
        ("excel_workbook", excel.get("excel_export_status", ""), Path(str(excel.get("workbook_output_path", "")))),
        ("command_manifest", REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY, manifest_path),
        ("command_summary", REAL_MATCH_ANALYSIS_COMMAND_PREVIEW_READY, summary_path),
    ]
    return pd.DataFrame([{
        "artifact_type": kind,
        "artifact_status": str(status),
        "artifact_path": str(Path(path).resolve()) if str(path) else "",
        "exists": Path(path).exists() if str(path) else False,
        "preview_only": True,
        "safe_for_review": True,
        "notes": "Preview artifact for human review; no production prediction or betting output.",
    } for kind, status, path in rows], columns=ARTIFACT_COLUMNS)


def _artifact_markdown(frame: pd.DataFrame) -> str:
    lines = ["# Real Match Analysis Artifact Index", "", "| artifact_type | artifact_status | exists | artifact_path |", "|---|---|---:|---|"]
    for _, row in frame.iterrows():
        lines.append(f"| {row['artifact_type']} | {row['artifact_status']} | {str(row['exists']).lower()} | {row['artifact_path']} |")
    lines.extend(["", "Preview-only index. No production prediction, betting output, position sizing, or financial return tracking.", ""])
    return "\n".join(lines)


def _summary(result: RealMatchAnalysisCommandResult) -> str:
    return "\n".join([
        "# Real Match Analysis Command Preview",
        "",
        f"- command_status: {result.command_status}",
        f"- human_report_path: {result.human_report_path}",
        f"- excel_workbook_path: {result.excel_workbook_path}",
        f"- artifact_index_path: {result.artifact_index_path}",
        "- preview-only command output",
        "- no production prediction, betting output, position sizing, or financial return tracking",
        "",
    ])


def _blocked_from_runner(runner: dict[str, object]) -> str:
    status = str(runner.get("match_analysis_runner_status", ""))
    if status == "MATCH_ANALYSIS_RUNNER_PREVIEW_READY":
        return ""
    if "UNKNOWN" in status:
        return REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_UNKNOWN_MATCH
    if "AMBIGUOUS" in status:
        return REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_AMBIGUOUS_MATCH
    if "CONTEXT_BUNDLE" in status:
        return REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_CONTEXT_BUNDLE
    if "CONTEXT_BRIDGE" in status:
        return REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_CONTEXT_BRIDGE
    if "REPORT" in status:
        return REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_REPORT
    return REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_CONTEXT_BUNDLE


def _has_selector(config: RealMatchAnalysisCommandConfig) -> bool:
    return any([
        config.understat_provider_match_id, config.fbref_provider_match_id,
        config.home_team, config.away_team, config.match_date,
        config.competition, config.season,
    ])


def _blocked_from_export(bundle: dict[str, object]) -> str:
    status = str(bundle.get("export_bundle_status", ""))
    if "UNKNOWN" in status:
        return REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_UNKNOWN_MATCH
    if "AMBIGUOUS" in status:
        return REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_AMBIGUOUS_MATCH
    if "UNSAFE" in status:
        return REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_UNSAFE_PATH
    return REAL_MATCH_ANALYSIS_COMMAND_BLOCKED_EXPORT_BUNDLE


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "real_match_analysis_command").resolve()
    return resolved if resolved == allowed or allowed in resolved.parents else None


def _safe_export_dir(path: str | Path | None, base: Path) -> Path | None:
    resolved = (base / "outputs" / "analysis_preview" / "match_analysis_export_bundle").resolve() if path is None else (base / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    allowed = (base / "outputs" / "analysis_preview" / "match_analysis_export_bundle").resolve()
    return resolved if resolved == allowed or allowed in resolved.parents else None


def _safe_excel_dir(path: str | Path | None, base: Path) -> Path | None:
    resolved = (base / "outputs" / "analysis_preview" / "match_analysis_excel_export").resolve() if path is None else (base / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    allowed = (base / "outputs" / "analysis_preview" / "match_analysis_excel_export").resolve()
    return resolved if resolved == allowed or allowed in resolved.parents else None


def _notes() -> str:
    return "; ".join([
        REAL_MATCH_ANALYSIS_COMMAND_NETWORK_DISABLED_BY_DESIGN,
        REAL_MATCH_ANALYSIS_COMMAND_NO_MODEL_INTEGRATION_BY_DESIGN,
        REAL_MATCH_ANALYSIS_COMMAND_NO_BETTING_INTEGRATION_BY_DESIGN,
        REAL_MATCH_ANALYSIS_COMMAND_NO_STAKING_INTEGRATION_BY_DESIGN,
    ])
