# -*- coding: utf-8 -*-
"""Build a v1.9 batch config from match pack validation preview."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v19_match_pack_contract_preview import validate_match_pack

V19_BATCH_CONFIG_BUILDER_PREVIEW_READY = "V19_BATCH_CONFIG_BUILDER_PREVIEW_READY"
BATCH_CONFIG_COLUMNS = ["match_id", "input_dir", "home_team", "away_team", "competition", "season", "match_date", "manual_evidence_completion", "run_transition_lab", "notes"]


@dataclass(frozen=True)
class V19BatchConfigBuilderConfig:
    manifest: str | Path
    output: str | Path
    include_partial: bool = True
    emit_all: bool = False
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19BatchConfigBuilderResult:
    batch_config_builder_status: str
    batch_config_builder_enabled: bool
    output_path: str
    report_path: str
    matches_included: int
    matches_excluded: int
    network_calls_enabled: bool
    prediction_logic_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19BatchConfigBuilder:
    def __init__(self, config: V19BatchConfigBuilderConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> V19BatchConfigBuilderResult:
        manifest = _resolve(self.config.manifest, self.base)
        rows = pd.read_csv(manifest, keep_default_na=False).to_dict(orient="records")
        validations = [validate_match_pack(row, base_dir=self.base).to_dict() for row in rows]
        output = _resolve(self.config.output, self.base)
        output.parent.mkdir(parents=True, exist_ok=True)
        included = []
        excluded = []
        for row, validation in zip(rows, validations):
            if validation.get("can_run_workbench") is True and (self.config.include_partial or validation.get("health_status") == "READY"):
                included.append(_batch_row(row))
            else:
                excluded.append({"match_id": row.get("match_id", ""), "reason": validation.get("errors") or validation.get("warnings") or "not runnable"})
        pd.DataFrame(included, columns=BATCH_CONFIG_COLUMNS).to_csv(output, index=False)
        report = output.with_name("auto_batch_config_report.md")
        report.write_text(_report(included, excluded), encoding="utf-8")
        return V19BatchConfigBuilderResult(V19_BATCH_CONFIG_BUILDER_PREVIEW_READY, True, str(output.resolve()), str(report.resolve()), len(included), len(excluded), False, False, False, False, False, V19_BATCH_CONFIG_BUILDER_PREVIEW_READY)


def _batch_row(row: dict[str, object]) -> dict[str, object]:
    return {
        "match_id": row.get("match_id", ""),
        "input_dir": row.get("input_dir", ""),
        "home_team": row.get("home_team", ""),
        "away_team": row.get("away_team", ""),
        "competition": row.get("competition", ""),
        "season": row.get("season", ""),
        "match_date": row.get("match_date", ""),
        "manual_evidence_completion": row.get("manual_evidence_completion", ""),
        "run_transition_lab": "false",
        "notes": row.get("notes", ""),
    }


def _report(included: list[dict[str, object]], excluded: list[dict[str, object]]) -> str:
    return "\n".join([
        "# v1.9 Auto Batch Config Report",
        "",
        "## Included Matches",
        _table(pd.DataFrame(included)),
        "",
        "## Excluded Matches",
        _table(pd.DataFrame(excluded)),
        "",
        "## Safety",
        "Preview only. No production betting. No stake. No ROI. No automatic betting.",
        "",
    ])


def _table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)


def _resolve(path: str | Path, base: Path) -> Path:
    p = Path(path)
    return p.resolve() if p.is_absolute() else (base / p).resolve()
