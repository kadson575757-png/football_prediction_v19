# -*- coding: utf-8 -*-
"""Apply a filled completion pack, rerun the workbench, and compare decisions."""
from __future__ import annotations

import shutil
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v19_decision_delta_preview import V19DecisionDeltaConfig, V19DecisionDeltaRunner
from football_prediction_v19.analysis.v19_match_workbench_preview import V19MatchWorkbenchConfig, V19MatchWorkbenchRunner

V19_COMPLETION_RERUN_PREVIEW_READY = "V19_COMPLETION_RERUN_PREVIEW_READY"
V19_COMPLETION_RERUN_BLOCKED_MISSING_INPUT = "V19_COMPLETION_RERUN_BLOCKED_MISSING_INPUT"


@dataclass(frozen=True)
class V19CompletionRerunConfig:
    base_workbench_json: str | Path
    filled_completion_csv: str | Path
    input_dir: str | Path
    home_team: str
    away_team: str
    competition: str
    season: str
    match_date: str
    output_dir: str | Path = "outputs/analysis_preview/v19_completion_rerun"
    emit_all: bool = False
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19CompletionRerunResult:
    completion_rerun_status: str
    applied_completion_path: str
    rerun_workbench_dashboard_path: str
    decision_delta_report_path: str
    decision_delta_json_path: str
    blocker_delta_path: str
    market_family_delta_path: str
    score_tree_delta_path: str
    readiness_delta_path: str
    rerun_bundle_index_path: str
    filled_values_count: int
    decision_delta_status: str
    decision_class_changed: bool
    evidence_readiness_delta: int
    promotion_changed: bool
    final_decision_class: str
    promotion_allowed: bool
    network_calls_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19CompletionRerunRunner:
    def __init__(self, config: V19CompletionRerunConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> V19CompletionRerunResult:
        out = _resolve(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)
        filled = _read_frame(_resolve(self.config.filled_completion_csv, self.base))
        base_json = _resolve(self.config.base_workbench_json, self.base)
        if filled.empty or not base_json.exists():
            return self._blocked()
        base_payload = _read_json(base_json)
        applied_path = out / "applied_completion.csv"
        filled_count = _write_applied_completion(filled, applied_path, self.config, base_payload)
        rerun_dir = out / "rerun_workbench"
        workbench = V19MatchWorkbenchRunner(
            V19MatchWorkbenchConfig(
                input_dir=self.config.input_dir,
                home_team=self.config.home_team,
                away_team=self.config.away_team,
                competition=self.config.competition,
                season=self.config.season,
                match_date=self.config.match_date,
                manual_evidence_completion=applied_path,
                emit_all=True,
                output_dir=rerun_dir,
                base_dir=self.base,
            )
        ).run()
        rerun_json = rerun_dir / "machine_readable_workbench.json"
        delta = V19DecisionDeltaRunner(
            V19DecisionDeltaConfig(
                base_workbench_json=base_json,
                rerun_workbench_json=rerun_json,
                filled_values_count=filled_count,
                output_dir=out,
                base_dir=self.base,
            )
        ).run()
        dashboard_copy = out / "rerun_workbench_dashboard.md"
        source_dashboard = Path(workbench.workbench_dashboard_path)
        if source_dashboard.exists():
            shutil.copyfile(source_dashboard, dashboard_copy)
        bundle = out / "rerun_bundle_index.csv"
        rows = _write_index(bundle, {
            "applied_completion": applied_path,
            "rerun_workbench_dashboard": dashboard_copy,
            "decision_delta_report": Path(delta.decision_delta_report_path),
            "decision_delta_json": Path(delta.decision_delta_json_path),
            "blocker_delta": Path(delta.blocker_delta_path),
            "market_family_delta": Path(delta.market_family_delta_path),
            "score_tree_delta": Path(delta.score_tree_delta_path),
            "readiness_delta": Path(delta.readiness_delta_path),
        })
        return V19CompletionRerunResult(
            V19_COMPLETION_RERUN_PREVIEW_READY,
            str(applied_path.resolve()),
            str(dashboard_copy.resolve()),
            delta.decision_delta_report_path,
            delta.decision_delta_json_path,
            delta.blocker_delta_path,
            delta.market_family_delta_path,
            delta.score_tree_delta_path,
            delta.readiness_delta_path,
            str(bundle.resolve()),
            filled_count,
            delta.decision_delta_status,
            delta.decision_class_changed,
            delta.evidence_readiness_delta,
            delta.promotion_changed,
            workbench.final_decision_class,
            workbench.promotion_allowed,
            False,
            False,
            False,
            False,
            V19_COMPLETION_RERUN_PREVIEW_READY,
        )

    def _blocked(self) -> V19CompletionRerunResult:
        return V19CompletionRerunResult(V19_COMPLETION_RERUN_BLOCKED_MISSING_INPUT, "", "", "", "", "", "", "", "", "", 0, "", False, 0, False, "", False, False, False, False, False, V19_COMPLETION_RERUN_BLOCKED_MISSING_INPUT)


def _write_applied_completion(filled: pd.DataFrame, path: Path, config: V19CompletionRerunConfig, base_payload: dict[str, object]) -> int:
    base_completion_path = str(base_payload.get("input", {}).get("manual_completion_file", "")).strip()
    base_completion = _read_frame(Path(base_completion_path)) if base_completion_path else pd.DataFrame()
    values = {
        "home_team": config.home_team,
        "away_team": config.away_team,
        "competition": config.competition,
        "season": config.season,
        "match_date": config.match_date,
        "cross_provider_match_key": _manual_key(config),
    }
    if not base_completion.empty:
        values.update(base_completion.iloc[0].to_dict())
    count = 0
    for _, row in filled.iterrows():
        field = str(row.get("field_name", "")).strip()
        value = str(row.get("user_value", "")).strip()
        if field and value:
            values[field] = value
            count += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([values]).to_csv(path, index=False)
    return count


def _manual_key(config: V19CompletionRerunConfig) -> str:
    import re
    def slug(value: object) -> str:
        return re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower()).strip("-")
    return f"manual-{slug(config.competition)}-{slug(config.season)}-{slug(config.home_team)}-{slug(config.away_team)}-{config.match_date}"


def _write_index(path: Path, paths: dict[str, Path]) -> list[dict[str, object]]:
    rows = [{"artifact_name": name, "path": str(p.resolve()), "status": "READY" if p.exists() else "MISSING"} for name, p in paths.items()]
    pd.DataFrame(rows).to_csv(path, index=False)
    return rows


def _read_frame(path: Path) -> pd.DataFrame:
    try:
        if not path.exists():
            return pd.DataFrame()
        return pd.read_csv(path, keep_default_na=False)
    except Exception:
        return pd.DataFrame()


def _read_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _resolve(path: str | Path, base: Path) -> Path:
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()
