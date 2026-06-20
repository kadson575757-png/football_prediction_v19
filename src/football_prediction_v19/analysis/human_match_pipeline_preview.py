# -*- coding: utf-8 -*-
"""End-to-end human match analysis pipeline preview."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

HUMAN_MATCH_PIPELINE_PREVIEW_READY = "HUMAN_MATCH_PIPELINE_PREVIEW_READY"
HUMAN_MATCH_PIPELINE_PREVIEW_PARTIAL_READY = "HUMAN_MATCH_PIPELINE_PREVIEW_PARTIAL_READY"
HUMAN_MATCH_PIPELINE_BLOCKED_IMPORTER = "HUMAN_MATCH_PIPELINE_BLOCKED_IMPORTER"
HUMAN_MATCH_PIPELINE_BLOCKED_INPUT_BUNDLE = "HUMAN_MATCH_PIPELINE_BLOCKED_INPUT_BUNDLE"
HUMAN_MATCH_PIPELINE_BLOCKED_SINGLE_MATCH_REPORT = "HUMAN_MATCH_PIPELINE_BLOCKED_SINGLE_MATCH_REPORT"
HUMAN_MATCH_PIPELINE_BLOCKED_CONTEXT_ENRICHMENT = "HUMAN_MATCH_PIPELINE_BLOCKED_CONTEXT_ENRICHMENT"
HUMAN_MATCH_PIPELINE_BLOCKED_HUMAN_REPORT = "HUMAN_MATCH_PIPELINE_BLOCKED_HUMAN_REPORT"
HUMAN_MATCH_PIPELINE_BLOCKED_UNSAFE_PATH = "HUMAN_MATCH_PIPELINE_BLOCKED_UNSAFE_PATH"
HUMAN_MATCH_PIPELINE_NETWORK_DISABLED_BY_DESIGN = "HUMAN_MATCH_PIPELINE_NETWORK_DISABLED_BY_DESIGN"
HUMAN_MATCH_PIPELINE_MODEL_DISABLED_BY_DESIGN = "HUMAN_MATCH_PIPELINE_MODEL_DISABLED_BY_DESIGN"
HUMAN_MATCH_PIPELINE_BETTING_DISABLED_BY_DESIGN = "HUMAN_MATCH_PIPELINE_BETTING_DISABLED_BY_DESIGN"

MANIFEST_COLUMNS = [
    "pipeline_run_id", "source_id", "provider_match_id", "league", "season",
    "final_report_path", "steps_checked", "steps_ready", "steps_failed",
    "rows_reported", "contexts_checked", "contexts_available",
    "contexts_missing_optional", "network_calls_enabled",
    "prediction_logic_enabled", "betting_logic_enabled", "pipeline_status",
    "recommendation", "notes",
]
STEP_COLUMNS = ["step_name", "step_status", "output_path", "warning", "recommendation", "notes"]


@dataclass(frozen=True)
class HumanMatchPipelinePreviewConfig:
    input_path: str | Path | None = None
    match_id: str | None = None
    output_dir: str | Path = "outputs/analysis_preview/human_match_pipeline"
    write_preview: bool = False
    base_dir: str | Path = "."
    pipeline_run_id: str = "human_match_pipeline_preview"


@dataclass(frozen=True)
class HumanMatchPipelinePreviewResult:
    pipeline_run_id: str
    source_id: str
    provider_match_id: str
    league: str
    season: str
    final_report_path: str
    steps_checked: int
    steps_ready: int
    steps_failed: int
    rows_reported: int
    contexts_checked: int
    contexts_available: int
    contexts_missing_optional: int
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    pipeline_status: str
    recommendation: str
    notes: str


class HumanMatchPipelinePreviewRunner:
    def __init__(self, config: HumanMatchPipelinePreviewConfig) -> None:
        self.config = config

    def validate_output_dir(self) -> Path | None:
        base = Path(self.config.base_dir).resolve()
        out = Path(self.config.output_dir)
        if not out.is_absolute():
            out = base / out
        resolved = out.resolve()
        allowed = (base / "outputs" / "analysis_preview" / "human_match_pipeline").resolve()
        if resolved == allowed or allowed in resolved.parents:
            return resolved
        return None


def build_manifest_frame(result: HumanMatchPipelinePreviewResult) -> pd.DataFrame:
    return pd.DataFrame([result.__dict__], columns=MANIFEST_COLUMNS)


def build_step_summary_frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=STEP_COLUMNS)


def build_markdown(result: HumanMatchPipelinePreviewResult, steps: pd.DataFrame) -> str:
    lines = [
        "# Phase 16.5 End-to-End Human Match Pipeline Preview",
        "",
        "This is a local end-to-end preview pipeline. No model prediction was run. No betting/staking recommendation was generated. No live external data was fetched.",
        "",
        "## Executive Summary",
        f"- pipeline_status: {result.pipeline_status}",
        f"- rows_reported: {result.rows_reported}",
        f"- steps_checked: {result.steps_checked}",
        f"- steps_ready: {result.steps_ready}",
        f"- steps_failed: {result.steps_failed}",
        f"- final_report_path: {result.final_report_path}",
        "",
        "## Step Summary",
        _markdown_table(steps),
        "",
        "## Safety Notes",
        "Missing values are not inferred or invented. Preview outputs remain separate from production model logic. Network, prediction, and betting/staking logic are disabled by design.",
        "",
        "## Recommendation",
        result.recommendation,
        "",
    ]
    return "\n".join(lines)


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No steps recorded."
    columns = list(frame.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row[column]).replace("|", ";") for column in columns) + " |")
    return "\n".join(lines)

