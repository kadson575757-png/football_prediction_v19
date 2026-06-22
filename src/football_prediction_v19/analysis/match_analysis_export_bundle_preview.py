# -*- coding: utf-8 -*-
"""Preview-only match analysis export bundle builder."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

import pandas as pd

MATCH_ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY = "MATCH_ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY"
MATCH_ANALYSIS_EXPORT_BUNDLE_BLOCKED_MISSING_INPUT = "MATCH_ANALYSIS_EXPORT_BUNDLE_BLOCKED_MISSING_INPUT"
MATCH_ANALYSIS_EXPORT_BUNDLE_BLOCKED_UNKNOWN_MATCH = "MATCH_ANALYSIS_EXPORT_BUNDLE_BLOCKED_UNKNOWN_MATCH"
MATCH_ANALYSIS_EXPORT_BUNDLE_BLOCKED_AMBIGUOUS_MATCH = "MATCH_ANALYSIS_EXPORT_BUNDLE_BLOCKED_AMBIGUOUS_MATCH"
MATCH_ANALYSIS_EXPORT_BUNDLE_BLOCKED_UNSAFE_PATH = "MATCH_ANALYSIS_EXPORT_BUNDLE_BLOCKED_UNSAFE_PATH"
MATCH_ANALYSIS_EXPORT_BUNDLE_NO_MODEL_INTEGRATION_BY_DESIGN = "MATCH_ANALYSIS_EXPORT_BUNDLE_NO_MODEL_INTEGRATION_BY_DESIGN"
MATCH_ANALYSIS_EXPORT_BUNDLE_NO_BETTING_INTEGRATION_BY_DESIGN = "MATCH_ANALYSIS_EXPORT_BUNDLE_NO_BETTING_INTEGRATION_BY_DESIGN"
MATCH_ANALYSIS_EXPORT_BUNDLE_NO_STAKING_INTEGRATION_BY_DESIGN = "MATCH_ANALYSIS_EXPORT_BUNDLE_NO_STAKING_INTEGRATION_BY_DESIGN"
MATCH_ANALYSIS_EXPORT_BUNDLE_NETWORK_DISABLED_BY_DESIGN = "MATCH_ANALYSIS_EXPORT_BUNDLE_NETWORK_DISABLED_BY_DESIGN"

MANIFEST_COLUMNS = [
    "export_bundle_run_id", "match_analysis_runner_status", "context_bridge_status",
    "v19_diagnostic_synthesis_status", "v19_diagnostic_gate_matrix_status",
    "odds_market_movement_input_status", "market_movement_diagnostic_status",
    "human_24_block_report_status", "match_date", "competition", "season",
    "home_team", "away_team", "understat_provider_match_id",
    "fbref_provider_match_id", "cross_provider_match_key", "rows_context",
    "rows_synthesis", "gates_evaluated", "gates_ready", "gates_blocked",
    "gates_disabled", "sections_rendered", "required_sections_rendered",
    "exported_files_count", "export_bundle_status", "recommendation", "notes",
    "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled",
    "staking_logic_enabled", "roi_logic_enabled",
]
PROTECTED = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]
EXPECTED_FILES = [
    "match_identity.csv", "context_human_input_review.csv",
    "v19_diagnostic_synthesis_review.csv", "v19_diagnostic_gate_matrix_review.csv",
    "odds_market_movement_input_review.csv", "market_movement_diagnostic_review.csv",
    "report_sections_review.csv", "export_safety_flags.csv",
]


@dataclass(frozen=True)
class MatchAnalysisExportBundleConfig:
    cross_provider_match_key: str | None = None
    understat_provider_match_id: str | None = None
    fbref_provider_match_id: str | None = None
    home_team: str | None = None
    away_team: str | None = None
    match_date: str | None = None
    competition: str | None = None
    season: str | None = None
    match_analysis_runner_manifest_path: str | Path | None = None
    context_human_input_path: str | Path | None = None
    v19_diagnostic_synthesis_path: str | Path | None = None
    v19_diagnostic_gate_matrix_path: str | Path | None = None
    odds_market_movement_input_path: str | Path | None = None
    market_movement_diagnostic_path: str | Path | None = None
    human_24_block_report_path: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/match_analysis_export_bundle"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class MatchAnalysisExportBundleResult:
    export_bundle_run_id: str
    export_bundle_dir: str
    manifest_path: str
    summary_path: str
    match_analysis_runner_status: str
    context_bridge_status: str
    v19_diagnostic_synthesis_status: str
    v19_diagnostic_gate_matrix_status: str
    odds_market_movement_input_status: str
    market_movement_diagnostic_status: str
    human_24_block_report_status: str
    match_date: str
    competition: str
    season: str
    home_team: str
    away_team: str
    understat_provider_match_id: str
    fbref_provider_match_id: str
    cross_provider_match_key: str
    rows_context: int
    rows_synthesis: int
    gates_evaluated: int
    gates_ready: int
    gates_blocked: int
    gates_disabled: int
    sections_rendered: int
    required_sections_rendered: int
    exported_files_count: int
    export_bundle_status: str
    recommendation: str
    notes: str
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool


class MatchAnalysisExportBundleRunner:
    def __init__(self, config: MatchAnalysisExportBundleConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> MatchAnalysisExportBundleResult:
        out = _safe_output(self.config.output_dir, self.base)
        if out is None or _has_unsafe_inputs(self.config):
            return self._blocked(MATCH_ANALYSIS_EXPORT_BUNDLE_BLOCKED_UNSAFE_PATH)
        paths = self._resolve_or_build()
        if paths.get("blocked"):
            return self._blocked(str(paths["blocked"]))
        required_paths = [paths.get(k) for k in ["runner_manifest", "context", "synthesis", "gate_matrix", "odds", "market", "report"]]
        if any(not p or not Path(str(p)).exists() for p in required_paths):
            return self._blocked(MATCH_ANALYSIS_EXPORT_BUNDLE_BLOCKED_MISSING_INPUT)

        context = pd.read_csv(paths["context"], low_memory=False)
        context_selected = _select(context, self.config)
        if context_selected.empty:
            return self._blocked(MATCH_ANALYSIS_EXPORT_BUNDLE_BLOCKED_UNKNOWN_MATCH)
        if len(context_selected) > 1:
            return self._blocked(MATCH_ANALYSIS_EXPORT_BUNDLE_BLOCKED_AMBIGUOUS_MATCH)
        context_row = context_selected.iloc[0]
        synthesis = pd.read_csv(paths["synthesis"], low_memory=False)
        gate_matrix = pd.read_csv(paths["gate_matrix"], low_memory=False)
        odds_input = pd.read_csv(paths["odds"], low_memory=False)
        market_diag = pd.read_csv(paths["market"], low_memory=False)
        runner_manifest = pd.read_csv(paths["runner_manifest"], low_memory=False)

        out.mkdir(parents=True, exist_ok=True)
        identity = pd.DataFrame([{
            "match_date": context_row.get("match_date", ""),
            "competition": context_row.get("competition", ""),
            "season": context_row.get("season", ""),
            "home_team": context_row.get("home_team", ""),
            "away_team": context_row.get("away_team", ""),
            "understat_provider_match_id": context_row.get("understat_provider_match_id", ""),
            "fbref_provider_match_id": context_row.get("fbref_provider_match_id", ""),
            "cross_provider_match_key": context_row.get("cross_provider_match_key", ""),
        }])
        identity.to_csv(out / "match_identity.csv", index=False)
        context_selected.to_csv(out / "context_human_input_review.csv", index=False)
        synthesis.to_csv(out / "v19_diagnostic_synthesis_review.csv", index=False)
        gate_matrix.to_csv(out / "v19_diagnostic_gate_matrix_review.csv", index=False)
        odds_input.to_csv(out / "odds_market_movement_input_review.csv", index=False)
        market_diag.to_csv(out / "market_movement_diagnostic_review.csv", index=False)
        _report_sections(Path(str(paths["report"]))).to_csv(out / "report_sections_review.csv", index=False)
        _safety_flags().to_csv(out / "export_safety_flags.csv", index=False)

        shutil.copyfile(paths["runner_manifest"], out / "match_analysis_runner_manifest_review.csv")
        exported_count = len([p for p in EXPECTED_FILES if (out / p).exists()])
        gate_status_counts = gate_matrix.get("gate_status", pd.Series(dtype=str)).astype(str).value_counts().to_dict()
        ready_count = int(gate_status_counts.get("DIAGNOSTIC_GATE_READY", 0))
        disabled_count = int(gate_status_counts.get("DIAGNOSTIC_GATE_DISABLED_NO_BETTING", 0) + gate_status_counts.get("DIAGNOSTIC_GATE_BLOCKED_BY_DESIGN", 0))
        blocked_count = int(gate_status_counts.get("DIAGNOSTIC_GATE_BLOCKED_MISSING_DATA", 0) + gate_status_counts.get("DIAGNOSTIC_GATE_REQUIRES_LATER_MODEL_PHASE", 0))
        report_sections = _report_sections(Path(str(paths["report"])))
        runner_row = runner_manifest.iloc[0] if not runner_manifest.empty else pd.Series(dtype=object)
        manifest_path = out / "match_analysis_export_bundle_manifest.csv"
        summary_path = out / "match_analysis_export_bundle_summary.md"
        result = MatchAnalysisExportBundleResult(
            "match_analysis_export_bundle_preview", str(out.resolve()), str(manifest_path.resolve()),
            str(summary_path.resolve()), str(runner_row.get("match_analysis_runner_status", "")),
            str(runner_row.get("context_bridge_status", "")),
            str(runner_row.get("v19_diagnostic_synthesis_status", "")),
            str(runner_row.get("v19_diagnostic_gate_matrix_status", "")),
            str(runner_row.get("odds_market_movement_input_status", "")),
            str(runner_row.get("market_movement_diagnostic_status", "")),
            str(runner_row.get("human_24_block_report_status", "")),
            str(context_row.get("match_date", "")), str(context_row.get("competition", "")),
            str(context_row.get("season", "")), str(context_row.get("home_team", "")),
            str(context_row.get("away_team", "")), str(context_row.get("understat_provider_match_id", "")),
            str(context_row.get("fbref_provider_match_id", "")), str(context_row.get("cross_provider_match_key", "")),
            len(context_selected), len(synthesis), len(gate_matrix), ready_count, blocked_count,
            disabled_count, len(report_sections), len(report_sections), exported_count,
            MATCH_ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY, MATCH_ANALYSIS_EXPORT_BUNDLE_PREVIEW_READY,
            _notes(), False, False, False, False, False,
        )
        pd.DataFrame([{c: getattr(result, c) for c in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest_path, index=False)
        summary_path.write_text(
            "\n".join([
                "# Match Analysis Export Bundle Preview",
                "",
                f"- export_bundle_status: {result.export_bundle_status}",
                f"- exported_files_count: {result.exported_files_count}",
                "- preview-only review bundle",
                "- no production prediction, betting output, position sizing, or financial return tracking",
                "",
            ]),
            encoding="utf-8",
        )
        return result

    def _resolve_or_build(self) -> dict[str, object]:
        runner_manifest = _resolve(self.config.match_analysis_runner_manifest_path, self.base)
        context = _resolve(self.config.context_human_input_path, self.base)
        synthesis = _resolve(self.config.v19_diagnostic_synthesis_path, self.base)
        gate_matrix = _resolve(self.config.v19_diagnostic_gate_matrix_path, self.base)
        odds = _resolve(self.config.odds_market_movement_input_path, self.base)
        market = _resolve(self.config.market_movement_diagnostic_path, self.base)
        report = _resolve(self.config.human_24_block_report_path, self.base)
        if not all([runner_manifest, context, synthesis, gate_matrix, odds, market, report]):
            from scripts.build_match_analysis_runner_preview import build_match_analysis_runner_preview

            runner = build_match_analysis_runner_preview(
                cross_provider_match_key=self.config.cross_provider_match_key or "u-bundesliga-2024-001",
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
            status = str(runner.get("match_analysis_runner_status", ""))
            if "UNKNOWN" in status:
                return {"blocked": MATCH_ANALYSIS_EXPORT_BUNDLE_BLOCKED_UNKNOWN_MATCH}
            if "AMBIGUOUS" in status:
                return {"blocked": MATCH_ANALYSIS_EXPORT_BUNDLE_BLOCKED_AMBIGUOUS_MATCH}
            runner_manifest = Path(str(runner.get("manifest_path", "")))
            report = Path(str(runner.get("report_output_path", "")))
            context = self.base / "outputs" / "analysis_preview" / "context_bundle_human_input" / "context_bundle_human_input.csv"
            synthesis = self.base / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis" / "v19_diagnostic_synthesis.csv"
            gate_matrix = self.base / "outputs" / "analysis_preview" / "v19_diagnostic_gate_matrix" / "v19_diagnostic_gate_matrix.csv"
            odds = self.base / "outputs" / "analysis_preview" / "odds_market_movement_input" / "odds_market_movement_input.csv"
            market = self.base / "outputs" / "analysis_preview" / "market_movement_diagnostic" / "market_movement_diagnostic.csv"
        return {"runner_manifest": runner_manifest, "context": context, "synthesis": synthesis, "gate_matrix": gate_matrix, "odds": odds, "market": market, "report": report}

    def _blocked(self, status: str) -> MatchAnalysisExportBundleResult:
        return MatchAnalysisExportBundleResult("match_analysis_export_bundle_preview", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", 0, 0, 0, 0, 0, 0, 0, 0, 0, status, status, _notes(), False, False, False, False, False)


def _select(frame: pd.DataFrame, config: MatchAnalysisExportBundleConfig) -> pd.DataFrame:
    selected = frame.copy()
    for column, value in [("cross_provider_match_key", config.cross_provider_match_key), ("understat_provider_match_id", config.understat_provider_match_id), ("fbref_provider_match_id", config.fbref_provider_match_id), ("home_team", config.home_team), ("away_team", config.away_team), ("competition", config.competition), ("season", config.season)]:
        if value and column in selected.columns:
            selected = selected[selected[column].astype(str).str.lower() == str(value).lower()]
    if config.match_date and "match_date" in selected.columns:
        selected = selected[selected["match_date"].astype(str).str[:10] == str(config.match_date)[:10]]
    return selected


def _report_sections(path: Path) -> pd.DataFrame:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    rows: list[dict[str, object]] = []
    current = ""
    buffer: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current:
                rows.append({"section": current, "body": "\n".join(buffer).strip()})
            current = line[3:].strip()
            buffer = []
        elif current:
            buffer.append(line)
    if current:
        rows.append({"section": current, "body": "\n".join(buffer).strip()})
    return pd.DataFrame(rows)


def _safety_flags() -> pd.DataFrame:
    return pd.DataFrame([{
        "network_calls_enabled": "false",
        "prediction_logic_enabled": "false",
        "betting_logic_enabled": "false",
        "staking_logic_enabled": "false",
        "roi_logic_enabled": "false",
        "safe_output_note": "Preview-only export; no production prediction, betting output, position sizing, or financial return tracking.",
    }])


def _safe_output(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "match_analysis_export_bundle").resolve()
    return resolved if resolved == allowed or allowed in resolved.parents else None


def _resolve(path: str | Path | None, base: Path) -> Path | None:
    if path is None:
        return None
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _has_unsafe_inputs(config: MatchAnalysisExportBundleConfig) -> bool:
    for value in [config.match_analysis_runner_manifest_path, config.context_human_input_path, config.v19_diagnostic_synthesis_path, config.v19_diagnostic_gate_matrix_path, config.odds_market_movement_input_path, config.market_movement_diagnostic_path, config.human_24_block_report_path]:
        if value and _unsafe(value):
            return True
    return False


def _unsafe(path: str | Path) -> bool:
    text = str(path).replace("\\", "/").lower()
    return text.startswith(("http://", "https://")) or any(token in text for token in PROTECTED)


def _notes() -> str:
    return "; ".join([
        MATCH_ANALYSIS_EXPORT_BUNDLE_NETWORK_DISABLED_BY_DESIGN,
        MATCH_ANALYSIS_EXPORT_BUNDLE_NO_MODEL_INTEGRATION_BY_DESIGN,
        MATCH_ANALYSIS_EXPORT_BUNDLE_NO_BETTING_INTEGRATION_BY_DESIGN,
        MATCH_ANALYSIS_EXPORT_BUNDLE_NO_STAKING_INTEGRATION_BY_DESIGN,
    ])
