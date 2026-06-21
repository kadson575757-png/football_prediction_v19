# -*- coding: utf-8 -*-
"""Provider-to-human match analysis bundle preview orchestration."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_human_match_pipeline_from_manual_input_preview import build_pipeline_from_manual_input  # noqa: E402
from build_manual_input_from_provider_match_finder_preview import build_manual_input_from_provider_match_finder_preview  # noqa: E402
from build_understat_provider_pull_preview import build_understat_provider_pull_preview  # noqa: E402
from football_prediction_v19.analysis.manual_human_match_input import (  # noqa: E402
    MANUAL_HUMAN_MATCH_INPUT_VALIDATION_READY,
    ManualHumanMatchInputConfig,
    ManualHumanMatchInputValidator,
)
from football_prediction_v19.importers.provider_match_finder_preview import (  # noqa: E402
    PROVIDER_MATCH_FINDER_PREVIEW_READY,
    ProviderMatchFinderConfig,
    ProviderMatchFinderPreview,
)

PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PREVIEW_READY = "PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PREVIEW_READY"
PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PARTIAL_READY = "PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PARTIAL_READY"
PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_PROVIDER_PULL = "PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_PROVIDER_PULL"
PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_MATCH_FINDER = "PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_MATCH_FINDER"
PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_MANUAL_BRIDGE = "PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_MANUAL_BRIDGE"
PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_VALIDATION = "PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_VALIDATION"
PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_HUMAN_PIPELINE = "PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_HUMAN_PIPELINE"
PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_UNSAFE_PATH = "PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_UNSAFE_PATH"
PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_NETWORK_DISABLED_BY_DESIGN = "PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_NETWORK_DISABLED_BY_DESIGN"
PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_MODEL_DISABLED_BY_DESIGN = "PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_MODEL_DISABLED_BY_DESIGN"
PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BETTING_DISABLED_BY_DESIGN = "PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BETTING_DISABLED_BY_DESIGN"

MANIFEST_COLUMNS = [
    "bundle_run_id", "provider", "source_id", "provider_match_id", "league", "season",
    "match_date", "home_team", "away_team", "provider_pull_status", "match_finder_status",
    "manual_input_bridge_status", "validation_status", "human_match_pipeline_status",
    "final_report_path", "rows_normalized", "candidates_checked", "candidates_matched",
    "rows_written", "rows_reported", "steps_checked", "steps_ready", "steps_failed",
    "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled",
    "bundle_status", "recommendation", "notes",
]
STEP_COLUMNS = ["step_name", "step_status", "output_path", "warning", "recommendation", "notes"]
PROTECTED_PATH_TOKENS = ["data/processed", "trusted_xg_sources/accepted", "trusted_xg_sources/raw", "manual_xg_manifest"]


@dataclass(frozen=True)
class ProviderToHumanAnalysisBundleConfig:
    provider: str = "understat"
    league: str = "Bundesliga"
    season: str = "2024"
    provider_match_id: str | None = "u-bundesliga-2024-001"
    home_team: str | None = None
    away_team: str | None = None
    match_date: str | None = None
    alias_registry: str | Path | None = None
    output_dir: str | Path = "outputs/analysis_preview/provider_to_human_bundle"
    allow_network: bool = False
    write_preview: bool = True
    build_missing: bool = True
    base_dir: str | Path = "."


@dataclass(frozen=True)
class ProviderToHumanAnalysisBundleResult:
    bundle_run_id: str
    provider: str
    source_id: str
    provider_match_id: str
    league: str
    season: str
    match_date: str
    home_team: str
    away_team: str
    provider_pull_status: str
    match_finder_status: str
    manual_input_bridge_status: str
    validation_status: str
    human_match_pipeline_status: str
    final_report_path: str
    rows_normalized: int
    candidates_checked: int
    candidates_matched: int
    rows_written: int
    rows_reported: int
    steps_checked: int
    steps_ready: int
    steps_failed: int
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    bundle_status: str
    recommendation: str
    notes: str
    manifest_path: str = ""
    step_summary_path: str = ""
    summary_path: str = ""


class ProviderToHumanAnalysisBundleRunner:
    def __init__(self, config: ProviderToHumanAnalysisBundleConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> tuple[ProviderToHumanAnalysisBundleResult, pd.DataFrame]:
        out = _safe_output_dir(self.config.output_dir, self.base)
        if out is None:
            return self._blocked(PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_UNSAFE_PATH), pd.DataFrame(columns=STEP_COLUMNS)
        steps: list[dict[str, object]] = []

        provider_pull = self._provider_pull()
        steps.append(_step("provider_pull", provider_pull.get("provider_pull_status", ""), provider_pull.get("normalized_output_path", ""), provider_pull.get("notes", ""), provider_pull.get("recommendation", ""), ""))
        if provider_pull.get("provider_pull_status") != "UNDERSTAT_PROVIDER_PULL_PREVIEW_READY":
            return self._finalize(out, self._blocked(PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_PROVIDER_PULL, provider_pull=provider_pull), steps)

        finder_result, _selected = ProviderMatchFinderPreview(
            ProviderMatchFinderConfig(
                normalized_input=provider_pull.get("normalized_output_path"),
                provider_match_id=self.config.provider_match_id,
                home_team=self.config.home_team,
                away_team=self.config.away_team,
                match_date=self.config.match_date,
                league=self.config.league,
                season=str(self.config.season),
                alias_registry=self.config.alias_registry,
                output_dir=self.base / "outputs" / "provider_pull_preview" / "match_finder",
                base_dir=self.base,
            )
        ).find()
        finder = finder_result.__dict__
        steps.append(_step("match_finder", finder["match_finder_status"], finder.get("selected_match_output_path", ""), finder.get("notes", ""), finder.get("recommendation", ""), ""))
        if finder["match_finder_status"] != PROVIDER_MATCH_FINDER_PREVIEW_READY:
            return self._finalize(out, self._blocked(PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_MATCH_FINDER, provider_pull=provider_pull, finder=finder), steps)

        bridge = build_manual_input_from_provider_match_finder_preview(
            selected_match=finder["selected_match_output_path"],
            output_dir=self.base / "outputs" / "analysis_preview" / "manual_input",
            base_dir=self.base,
        )
        steps.append(_step("manual_input_bridge", bridge.get("manual_input_bridge_status", ""), bridge.get("output_path", ""), "", bridge.get("recommendation", ""), ""))
        if bridge.get("manual_input_bridge_status") != "MANUAL_INPUT_FROM_PROVIDER_MATCH_FINDER_READY":
            return self._finalize(out, self._blocked(PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_MANUAL_BRIDGE, provider_pull=provider_pull, finder=finder, bridge=bridge), steps)

        validator = ManualHumanMatchInputValidator(ManualHumanMatchInputConfig(input_path=bridge["output_path"], output_dir=self.base / "outputs" / "analysis_preview" / "manual_input", base_dir=self.base))
        validation_result, _manual = validator.validate()
        validation = validation_result.__dict__
        validator.write_outputs(validation_result)
        steps.append(_step("manual_input_validation", validation["validation_status"], bridge.get("output_path", ""), validation.get("notes", ""), validation.get("recommendation", ""), ""))
        if validation["validation_status"] != MANUAL_HUMAN_MATCH_INPUT_VALIDATION_READY:
            return self._finalize(out, self._blocked(PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_VALIDATION, provider_pull=provider_pull, finder=finder, bridge=bridge, validation=validation), steps)

        pipeline = build_pipeline_from_manual_input(
            input_path=bridge["output_path"],
            output_dir=self.base / "outputs" / "analysis_preview" / "human_match_pipeline",
            base_dir=self.base,
        )
        steps.append(_step("human_match_pipeline", pipeline.get("human_match_pipeline_status", ""), pipeline.get("final_report_path", ""), pipeline.get("notes", ""), pipeline.get("recommendation", ""), ""))
        if pipeline.get("human_match_pipeline_status") != "HUMAN_MATCH_PIPELINE_PREVIEW_READY":
            return self._finalize(out, self._blocked(PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_HUMAN_PIPELINE, provider_pull=provider_pull, finder=finder, bridge=bridge, validation=validation, pipeline=pipeline), steps)

        result = self._ready(provider_pull=provider_pull, finder=finder, bridge=bridge, validation=validation, pipeline=pipeline)
        return self._finalize(out, result, steps)

    def _provider_pull(self) -> dict[str, object]:
        if self.config.provider != "understat":
            return {"provider_pull_status": PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_PROVIDER_PULL, "recommendation": PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_PROVIDER_PULL}
        normalized = _default_normalized(self.base)
        if normalized.exists() and not self.config.build_missing:
            return {
                "provider_pull_status": "UNDERSTAT_PROVIDER_PULL_PREVIEW_READY",
                "provider": "understat",
                "source_id": "understat_existing_preview",
                "league": self.config.league,
                "season": str(self.config.season),
                "normalized_output_path": str(normalized.resolve()),
                "rows_normalized": len(pd.read_csv(normalized, low_memory=False)),
                "network_calls_enabled": False,
                "recommendation": "UNDERSTAT_PROVIDER_PULL_PREVIEW_READY",
                "notes": PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_NETWORK_DISABLED_BY_DESIGN,
            }
        if not self.config.build_missing:
            return {"provider_pull_status": PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_PROVIDER_PULL, "recommendation": PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BLOCKED_PROVIDER_PULL, "rows_normalized": 0}
        fixture = ROOT / "tests" / "fixtures" / "understat" / "understat_bundesliga_2024_fixture.json"
        return build_understat_provider_pull_preview(
            league=self.config.league,
            season=str(self.config.season),
            input_path=fixture if not self.config.allow_network else None,
            output_dir=self.base / "outputs" / "provider_pull_preview" / "understat",
            allow_network=self.config.allow_network,
            write_preview=True,
            base_dir=self.base,
        )

    def _ready(self, *, provider_pull: dict[str, object], finder: dict[str, object], bridge: dict[str, object], validation: dict[str, object], pipeline: dict[str, object]) -> ProviderToHumanAnalysisBundleResult:
        return self._result(
            status=PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_PREVIEW_READY,
            provider_pull=provider_pull,
            finder=finder,
            bridge=bridge,
            validation=validation,
            pipeline=pipeline,
            notes=_safety_notes(),
        )

    def _blocked(self, status: str, *, provider_pull: dict[str, object] | None = None, finder: dict[str, object] | None = None, bridge: dict[str, object] | None = None, validation: dict[str, object] | None = None, pipeline: dict[str, object] | None = None) -> ProviderToHumanAnalysisBundleResult:
        return self._result(status=status, provider_pull=provider_pull or {}, finder=finder or {}, bridge=bridge or {}, validation=validation or {}, pipeline=pipeline or {}, notes=_safety_notes())

    def _result(self, *, status: str, provider_pull: dict[str, object], finder: dict[str, object], bridge: dict[str, object], validation: dict[str, object], pipeline: dict[str, object], notes: str) -> ProviderToHumanAnalysisBundleResult:
        return ProviderToHumanAnalysisBundleResult(
            bundle_run_id="provider_to_human_analysis_bundle_preview",
            provider=str(finder.get("provider") or provider_pull.get("provider") or self.config.provider),
            source_id=str(finder.get("source_id") or provider_pull.get("source_id", "")),
            provider_match_id=str(finder.get("provider_match_id") or self.config.provider_match_id or ""),
            league=str(finder.get("league") or self.config.league),
            season=str(finder.get("season") or self.config.season),
            match_date=str(finder.get("match_date") or self.config.match_date or ""),
            home_team=str(finder.get("home_team", "")),
            away_team=str(finder.get("away_team", "")),
            provider_pull_status=str(provider_pull.get("provider_pull_status", "")),
            match_finder_status=str(finder.get("match_finder_status", "")),
            manual_input_bridge_status=str(bridge.get("manual_input_bridge_status", "")),
            validation_status=str(validation.get("validation_status", "")),
            human_match_pipeline_status=str(pipeline.get("human_match_pipeline_status", "")),
            final_report_path=str(pipeline.get("final_report_path", "")),
            rows_normalized=int(provider_pull.get("rows_normalized", 0) or 0),
            candidates_checked=int(finder.get("candidates_checked", 0) or 0),
            candidates_matched=int(finder.get("candidates_matched", 0) or 0),
            rows_written=int(bridge.get("rows_written", 0) or 0),
            rows_reported=int(pipeline.get("rows_reported", 0) or 0),
            steps_checked=int(pipeline.get("steps_checked", 0) or 0),
            steps_ready=int(pipeline.get("steps_ready", 0) or 0),
            steps_failed=int(pipeline.get("steps_failed", 0) or 0),
            network_calls_enabled=any(_as_bool(x.get("network_calls_enabled", False)) for x in [provider_pull, finder, bridge, validation, pipeline]),
            prediction_logic_enabled=any(_as_bool(x.get("prediction_logic_enabled", False)) for x in [finder, bridge, validation, pipeline]),
            betting_logic_enabled=any(_as_bool(x.get("betting_logic_enabled", False)) for x in [finder, bridge, validation, pipeline]),
            bundle_status=status,
            recommendation=status,
            notes=notes,
        )

    def _finalize(self, out: Path, result: ProviderToHumanAnalysisBundleResult, steps: list[dict[str, object]]) -> tuple[ProviderToHumanAnalysisBundleResult, pd.DataFrame]:
        step_frame = pd.DataFrame(steps, columns=STEP_COLUMNS)
        if self.config.write_preview:
            out.mkdir(parents=True, exist_ok=True)
            manifest = out / "provider_to_human_analysis_bundle_manifest.csv"
            step_path = out / "provider_to_human_analysis_bundle_step_summary.csv"
            summary = out / "provider_to_human_analysis_bundle_summary.md"
            result = ProviderToHumanAnalysisBundleResult(**{**result.__dict__, "manifest_path": str(manifest.resolve()), "step_summary_path": str(step_path.resolve()), "summary_path": str(summary.resolve())})
            pd.DataFrame([{column: getattr(result, column) for column in MANIFEST_COLUMNS}], columns=MANIFEST_COLUMNS).to_csv(manifest, index=False)
            step_frame.to_csv(step_path, index=False)
            summary.write_text(_markdown(result, step_frame), encoding="utf-8")
        return result, step_frame


def _safe_output_dir(output_dir: str | Path, base: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base / out
    resolved = out.resolve()
    allowed = (base / "outputs" / "analysis_preview" / "provider_to_human_bundle").resolve()
    if resolved == allowed or allowed in resolved.parents:
        return resolved
    return None


def _default_normalized(base: Path) -> Path:
    normalized_dir = base / "outputs" / "provider_pull_preview" / "understat" / "normalized"
    matches = sorted(normalized_dir.glob("*_normalized_preview.csv"))
    return matches[0] if matches else normalized_dir / "understat_provider_pull_normalized.csv"


def _step(name: str, status: object, path: object, warning: object, recommendation: object, notes: object) -> dict[str, object]:
    return {"step_name": name, "step_status": status, "output_path": path, "warning": warning, "recommendation": recommendation, "notes": notes}


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _safety_notes() -> str:
    return f"{PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_NETWORK_DISABLED_BY_DESIGN}; {PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_MODEL_DISABLED_BY_DESIGN}; {PROVIDER_TO_HUMAN_ANALYSIS_BUNDLE_BETTING_DISABLED_BY_DESIGN}"


def _markdown(result: ProviderToHumanAnalysisBundleResult, steps: pd.DataFrame) -> str:
    return "\n".join([
        "# Provider-to-Human Analysis Bundle Preview",
        "",
        f"- bundle_status: {result.bundle_status}",
        f"- provider_match_id: {result.provider_match_id}",
        f"- rows_reported: {result.rows_reported}",
        f"- steps_failed: {result.steps_failed}",
        "",
        "## Step Summary",
        _markdown_table(steps),
        "",
        "No live network calls, model predictions, or betting/staking recommendations are enabled by this preview.",
        "",
    ])


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No steps recorded."
    columns = list(frame.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row[column]).replace("|", ";") for column in columns) + " |")
    return "\n".join(lines)
