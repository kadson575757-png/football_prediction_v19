# -*- coding: utf-8 -*-
"""Scenario batch lab preview for portfolio-level transitions."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v19_portfolio_delta_preview import compute_portfolio_delta

V19_SCENARIO_BATCH_LAB_PREVIEW_READY = "V19_SCENARIO_BATCH_LAB_PREVIEW_READY"


SCENARIOS = [
    ("BATCH_EMPTY_CONTROL", "ANALYST_LEAN_ONLY", False, False),
    ("BATCH_POSITIVE_CANDIDATE", "BET_CANDIDATE_PREVIEW", True, False),
    ("BATCH_STRONG_CANDIDATE", "STRONG_BET_CANDIDATE_PREVIEW", True, True),
    ("BATCH_NO_BET", "NO_BET_RECOMMENDED", False, False),
    ("BATCH_CONFLICT", "CONFLICT_REVIEW", False, False),
]


@dataclass(frozen=True)
class V19ScenarioBatchLabConfig:
    base_batch_results_json: str | Path
    output_dir: str | Path = "outputs/analysis_preview/v19_scenario_batch_lab"
    emit_all: bool = False
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19ScenarioBatchLabResult:
    scenario_batch_lab_status: str
    scenario_batch_lab_dashboard_path: str
    scenario_batch_matrix_path: str
    scenario_batch_matrix_md_path: str
    scenario_batch_results_json_path: str
    scenario_batch_bundle_index_path: str
    scenarios_total: int
    scenarios_passed: int
    network_calls_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19ScenarioBatchLabRunner:
    def __init__(self, config: V19ScenarioBatchLabConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> V19ScenarioBatchLabResult:
        base = _read_json(_resolve(self.config.base_batch_results_json, self.base))
        out = _resolve(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)
        rows = []
        results = []
        for scenario_id, target_class, promotion, strong in SCENARIOS:
            rerun = _scenario_payload(base, target_class, promotion, strong)
            delta = compute_portfolio_delta(base, rerun, missing_fields_filled_total=0 if scenario_id == "BATCH_EMPTY_CONTROL" else 27)
            expected_passed = _expected_delta(scenario_id, delta)
            row = {"scenario_id": scenario_id, "target_class": target_class, "candidate_count_delta": delta.candidate_count_delta, "strong_candidate_count_delta": delta.strong_candidate_count_delta, "no_bet_count_delta": delta.no_bet_count_delta, "conflict_review_count_delta": delta.conflict_review_count_delta, "status": "PASSED" if expected_passed else "FAILED"}
            rows.append(row)
            results.append({"scenario_id": scenario_id, "delta": delta.__dict__, "status": row["status"], "test_scenario_mode": True, "synthetic_completion_values": True})
        paths = {"dashboard": out / "scenario_batch_lab_dashboard.md", "matrix": out / "scenario_batch_matrix.csv", "matrix_md": out / "scenario_batch_matrix.md", "results": out / "scenario_batch_results.json", "bundle": out / "scenario_batch_bundle_index.csv"}
        matrix = pd.DataFrame(rows)
        matrix.to_csv(paths["matrix"], index=False)
        paths["matrix_md"].write_text("# v1.9 Scenario Batch Matrix\n\n" + _table(matrix) + "\n", encoding="utf-8")
        payload = {"scenario_batch_lab_status": V19_SCENARIO_BATCH_LAB_PREVIEW_READY, "test_scenario_mode": True, "synthetic_completion_values": True, "scenarios": results, "safety": _safety()}
        paths["results"].write_text(json.dumps(payload, indent=2), encoding="utf-8")
        paths["dashboard"].write_text(_dashboard(matrix), encoding="utf-8")
        _write_bundle(paths["bundle"], paths)
        return V19ScenarioBatchLabResult(V19_SCENARIO_BATCH_LAB_PREVIEW_READY, str(paths["dashboard"].resolve()), str(paths["matrix"].resolve()), str(paths["matrix_md"].resolve()), str(paths["results"].resolve()), str(paths["bundle"].resolve()), len(rows), len([r for r in rows if r["status"] == "PASSED"]), False, False, False, False, V19_SCENARIO_BATCH_LAB_PREVIEW_READY)


def _scenario_payload(base: dict[str, object], target_class: str, promotion: bool, strong: bool) -> dict[str, object]:
    payload = json.loads(json.dumps(base))
    for match in payload.get("matches", []):
        match["final_decision_class"] = target_class
        match["promotion_allowed"] = promotion
        match["strong_promotion_allowed"] = strong
        if promotion:
            match["evidence_readiness_score"] = 94 if strong else 90
        if target_class in {"BET_CANDIDATE_PREVIEW", "STRONG_BET_CANDIDATE_PREVIEW"}:
            match["critical_blockers_count"] = 1
    return payload


def _expected_delta(scenario_id: str, delta: object) -> bool:
    if scenario_id == "BATCH_EMPTY_CONTROL":
        return delta.candidate_count_delta == 0 and delta.average_readiness_delta == 0
    if scenario_id == "BATCH_POSITIVE_CANDIDATE":
        return delta.candidate_count_delta == 1
    if scenario_id == "BATCH_STRONG_CANDIDATE":
        return delta.strong_candidate_count_delta == 1
    if scenario_id == "BATCH_NO_BET":
        return delta.no_bet_count_delta == 1
    if scenario_id == "BATCH_CONFLICT":
        return delta.conflict_review_count_delta == 1
    return False


def _dashboard(matrix: pd.DataFrame) -> str:
    return "# v1.9 Scenario Batch Lab Dashboard\n\n" + _table(matrix) + "\n\nSynthetic/test mode only. No stake. No ROI.\n"


def _table(frame: pd.DataFrame) -> str:
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)


def _write_bundle(path: Path, paths: dict[str, Path]) -> None:
    pd.DataFrame([{"artifact_name": name, "path": str(p.resolve()), "status": "READY" if p.exists() else "MISSING"} for name, p in paths.items()]).to_csv(path, index=False)


def _read_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _resolve(path: str | Path, base: Path) -> Path:
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _safety() -> dict[str, bool]:
    return {"network_calls_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}
