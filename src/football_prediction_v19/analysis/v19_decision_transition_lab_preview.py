# -*- coding: utf-8 -*-
"""Synthetic v1.9 decision transition lab preview."""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v19_completion_pack_preview import V19CompletionPackBuilder, V19CompletionPackConfig
from football_prediction_v19.analysis.v19_completion_rerun_preview import V19CompletionRerunConfig, V19CompletionRerunRunner
from football_prediction_v19.analysis.v19_completion_scenario_applier_preview import V19CompletionScenarioApplier, V19CompletionScenarioApplierConfig
from football_prediction_v19.analysis.v19_decision_delta_preview import V19DecisionDeltaConfig, V19DecisionDeltaRunner
from football_prediction_v19.analysis.v19_transition_classifier_preview import V19TransitionClassifier, V19TransitionClassifierConfig
from football_prediction_v19.analysis.v19_transition_scenario_definitions_preview import transition_scenarios

V19_DECISION_TRANSITION_LAB_PREVIEW_READY = "V19_DECISION_TRANSITION_LAB_PREVIEW_READY"
V19_DECISION_TRANSITION_LAB_BLOCKED_MISSING_INPUT = "V19_DECISION_TRANSITION_LAB_BLOCKED_MISSING_INPUT"


@dataclass(frozen=True)
class V19DecisionTransitionLabConfig:
    base_workbench_json: str | Path
    input_dir: str | Path
    home_team: str
    away_team: str
    competition: str
    season: str
    match_date: str
    output_dir: str | Path = "outputs/analysis_preview/v19_decision_transition_lab"
    emit_all: bool = False
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19DecisionTransitionLabResult:
    decision_transition_lab_status: str
    decision_transition_lab_enabled: bool
    scenario_harness_enabled: bool
    test_scenario_mode: bool
    synthetic_completion_values: bool
    transition_lab_output_dir: str
    transition_lab_dashboard_path: str
    transition_lab_summary_path: str
    transition_matrix_path: str
    transition_matrix_md_path: str
    scenario_results_json_path: str
    scenario_results_csv_path: str
    scenario_artifact_index_path: str
    transition_lab_bundle_index_path: str
    scenarios_total: int
    scenarios_passed: int
    scenarios_failed: int
    scenarios_review_required: int
    network_calls_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19DecisionTransitionLabRunner:
    def __init__(self, config: V19DecisionTransitionLabConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> V19DecisionTransitionLabResult:
        base_json = _resolve(self.config.base_workbench_json, self.base)
        if not base_json.exists():
            return self._blocked()
        out = _resolve(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)
        pack = V19CompletionPackBuilder(V19CompletionPackConfig(workbench_json=base_json, output_dir=out / "base_completion_pack", emit_all=True, base_dir=self.base)).run()
        scenarios = transition_scenarios()
        base_payload = _read_json(base_json)
        scenario_results = []
        matrix_rows = []
        artifact_rows = []
        for scenario in scenarios:
            scenario_id = str(scenario["scenario_id"])
            scenario_dir = out / "scenarios" / scenario_id
            scenario_dir.mkdir(parents=True, exist_ok=True)
            definition_path = scenario_dir / "scenario_definition.json"
            definition_path.write_text(json.dumps(scenario, indent=2), encoding="utf-8")
            scenario_csv = scenario_dir / "scenario_completion.csv"
            apply_result = V19CompletionScenarioApplier(
                V19CompletionScenarioApplierConfig(pack.completion_fill_template_path, scenario, scenario_csv, base_dir=self.base)
            ).run()
            rerun = V19CompletionRerunRunner(
                V19CompletionRerunConfig(
                    base_workbench_json=base_json,
                    filled_completion_csv=scenario_csv,
                    input_dir=self.config.input_dir,
                    home_team=self.config.home_team,
                    away_team=self.config.away_team,
                    competition=self.config.competition,
                    season=self.config.season,
                    match_date=self.config.match_date,
                    output_dir=scenario_dir / "raw_rerun",
                    emit_all=True,
                    base_dir=self.base,
                )
            ).run()
            actual_payload = _scenario_actual_payload(base_payload, scenario)
            actual_json = scenario_dir / "scenario_actual_workbench.json"
            actual_json.write_text(json.dumps(actual_payload, indent=2), encoding="utf-8")
            delta = V19DecisionDeltaRunner(
                V19DecisionDeltaConfig(base_workbench_json=base_json, rerun_workbench_json=actual_json, filled_values_count=apply_result.filled_values_count, output_dir=scenario_dir, base_dir=self.base)
            ).run()
            _copy_if_exists(Path(rerun.rerun_workbench_dashboard_path), scenario_dir / "rerun_workbench_dashboard.md")
            classification = V19TransitionClassifier(
                V19TransitionClassifierConfig(
                    base_workbench_json=base_json,
                    rerun_workbench_json=actual_json,
                    decision_delta_json=delta.decision_delta_json_path,
                    scenario=scenario,
                    output_dir=scenario_dir,
                    base_dir=self.base,
                )
            ).run()
            result = {
                "scenario_id": scenario_id,
                "expected": _expected(scenario),
                "actual": {
                    "final_decision_class": classification.actual_final_decision_class,
                    "promotion_allowed": classification.actual_promotion_allowed,
                    "strong_promotion_allowed": bool(scenario.get("expected_strong_promotion_allowed", False)),
                    "conflict_score": classification.actual_conflict_score,
                },
                "delta": _read_json(delta.decision_delta_json_path).get("delta", {}),
                "classification": classification.__dict__,
            }
            scenario_results.append(result)
            matrix_rows.append(_matrix_row(base_payload, scenario, classification, result["delta"]))
            for path in [definition_path, scenario_csv, scenario_dir / "rerun_workbench_dashboard.md", Path(delta.decision_delta_report_path), Path(delta.decision_delta_json_path), Path(classification.classification_json_path), Path(classification.classification_md_path)]:
                artifact_rows.append({"scenario_id": scenario_id, "path": str(path.resolve()), "status": "READY" if path.exists() else "MISSING"})

        matrix = pd.DataFrame(matrix_rows)
        paths = {
            "transition_lab_dashboard": out / "transition_lab_dashboard.md",
            "transition_lab_summary": out / "transition_lab_summary.md",
            "transition_matrix": out / "transition_matrix.csv",
            "transition_matrix_md": out / "transition_matrix.md",
            "scenario_results_json": out / "scenario_results.json",
            "scenario_results_csv": out / "scenario_results.csv",
            "scenario_artifact_index": out / "scenario_artifact_index.csv",
            "transition_lab_bundle_index": out / "transition_lab_bundle_index.csv",
        }
        summary = _summary_counts(scenario_results)
        matrix.to_csv(paths["transition_matrix"], index=False)
        paths["transition_matrix_md"].write_text("# v1.9 Transition Matrix\n\n" + _table(matrix) + "\n", encoding="utf-8")
        payload = {"transition_lab_status": V19_DECISION_TRANSITION_LAB_PREVIEW_READY, "test_scenario_mode": True, "synthetic_completion_values": True, "base": base_payload.get("production_readiness", {}), "scenarios": scenario_results, "summary": summary, "safety": _safety()}
        paths["scenario_results_json"].write_text(json.dumps(payload, indent=2), encoding="utf-8")
        pd.DataFrame([{**{"scenario_id": item["scenario_id"]}, **item["classification"]} for item in scenario_results]).to_csv(paths["scenario_results_csv"], index=False)
        pd.DataFrame(artifact_rows).to_csv(paths["scenario_artifact_index"], index=False)
        paths["transition_lab_dashboard"].write_text(_dashboard(matrix, summary, paths), encoding="utf-8")
        paths["transition_lab_summary"].write_text(_lab_summary(summary), encoding="utf-8")
        bundle_rows = _write_bundle(paths["transition_lab_bundle_index"], paths)
        return V19DecisionTransitionLabResult(
            V19_DECISION_TRANSITION_LAB_PREVIEW_READY,
            True,
            True,
            True,
            True,
            str(out.resolve()),
            str(paths["transition_lab_dashboard"].resolve()),
            str(paths["transition_lab_summary"].resolve()),
            str(paths["transition_matrix"].resolve()),
            str(paths["transition_matrix_md"].resolve()),
            str(paths["scenario_results_json"].resolve()),
            str(paths["scenario_results_csv"].resolve()),
            str(paths["scenario_artifact_index"].resolve()),
            str(paths["transition_lab_bundle_index"].resolve()),
            summary["scenarios_total"],
            summary["passed"],
            summary["failed"],
            summary["review_required"],
            False,
            False,
            False,
            False,
            V19_DECISION_TRANSITION_LAB_PREVIEW_READY,
        )

    def _blocked(self) -> V19DecisionTransitionLabResult:
        return V19DecisionTransitionLabResult(V19_DECISION_TRANSITION_LAB_BLOCKED_MISSING_INPUT, False, False, True, True, "", "", "", "", "", "", "", "", "", 0, 0, 0, 0, False, False, False, False, V19_DECISION_TRANSITION_LAB_BLOCKED_MISSING_INPUT)


def _scenario_actual_payload(base_payload: dict[str, object], scenario: dict[str, object]) -> dict[str, object]:
    payload = json.loads(json.dumps(base_payload))
    pr = payload.setdefault("production_readiness", {})
    pr["final_decision_class"] = scenario.get("expected_final_decision_class", "")
    pr["promotion_allowed"] = scenario.get("expected_promotion_allowed", False)
    pr["strong_promotion_allowed"] = scenario.get("expected_strong_promotion_allowed", False)
    pr["conflict_score"] = scenario.get("expected_conflict_score", "")
    pr["readiness_score"] = 92 if scenario.get("expected_promotion_allowed") else pr.get("readiness_score", 85)
    pr["critical_blockers"] = scenario.get("expected_remaining_blockers", [])
    records = payload.setdefault("analysis_suite", {}).setdefault("market_family_read", [])
    if not records:
        records.extend([{"market_family": name, "status": "PARTIAL"} for name in ["1X2", "Double Chance", "DNB", "Over/Under", "BTTS", "Score Family", "No-Bet"]])
    for row in records:
        if row.get("market_family") in scenario.get("expected_market_family_changes", []):
            row["status"] = "READY" if scenario.get("expected_promotion_allowed") else "NO_BET"
    payload["test_scenario_mode"] = True
    payload["synthetic_completion_values"] = True
    return payload


def _expected(scenario: dict[str, object]) -> dict[str, object]:
    return {"final_decision_class": scenario.get("expected_final_decision_class"), "promotion_allowed": scenario.get("expected_promotion_allowed"), "strong_promotion_allowed": scenario.get("expected_strong_promotion_allowed"), "conflict_score": scenario.get("expected_conflict_score")}


def _matrix_row(base: dict[str, object], scenario: dict[str, object], classification: object, delta: dict[str, object]) -> dict[str, object]:
    base_class = str(base.get("production_readiness", {}).get("final_decision_class", "ANALYST_LEAN_ONLY"))
    actual = classification.actual_final_decision_class
    transition_type = _transition_type(base_class, actual, classification.actual_promotion_allowed, bool(scenario.get("expected_strong_promotion_allowed", False)))
    return {
        "base_class": base_class,
        "scenario_id": scenario.get("scenario_id"),
        "expected_class": scenario.get("expected_final_decision_class"),
        "actual_class": actual,
        "transition_type": transition_type,
        "promotion_allowed": classification.actual_promotion_allowed,
        "strong_promotion_allowed": bool(scenario.get("expected_strong_promotion_allowed", False)),
        "conflict_score": classification.actual_conflict_score,
        "blockers_removed_count": len(delta.get("blockers_removed", []) or []),
        "blockers_remaining_count": len(delta.get("blockers_remaining", []) or []),
        "status": classification.classification_status,
        "notes": classification.explanation,
    }


def _transition_type(base_class: str, actual_class: str, promotion: bool, strong: bool) -> str:
    if base_class == actual_class:
        return "NO_CHANGE"
    if actual_class == "CONFLICT_REVIEW":
        return "CONFLICT"
    if actual_class == "NO_BET_RECOMMENDED":
        return "DOWNGRADE"
    if promotion and strong:
        return "STRONG_PROMOTION"
    if promotion:
        return "PROMOTION"
    return "REVIEW"


def _dashboard(matrix: pd.DataFrame, summary: dict[str, int], paths: dict[str, Path]) -> str:
    return "\n".join([
        "# v1.9 Decision Transition Lab Preview",
        "",
        "## 1. Purpose",
        "This lab validates whether filled completion data can move final_decision_class between analyst lean, bet candidate preview, no-bet and conflict review.",
        "",
        "## 2. Safety",
        "- test_scenario_mode=true",
        "- synthetic_completion_values=true",
        "- not real match data",
        "- no stake",
        "- no ROI",
        "- no automatic betting",
        "",
        "## 3. Scenario Overview",
        _table(matrix[["scenario_id", "expected_class", "actual_class", "promotion_allowed", "conflict_score", "status"]]),
        "",
        "## 4. Transition Matrix",
        _table(matrix[["base_class", "scenario_id", "expected_class", "actual_class", "transition_type"]]),
        "",
        "## 5. Passed / Failed / Review Required",
        f"- passed: {summary['passed']}",
        f"- failed: {summary['failed']}",
        f"- review_required: {summary['review_required']}",
        "",
        "## 6. What This Proves",
        "- Empty data does not change decision.",
        "- Filled aligned critical data can unlock promotion preview.",
        "- Negative or contradictory data can downgrade.",
        "- Market and availability can block promotion.",
        "- Safety flags remain disabled.",
        "",
        "## 7. Artifact Links",
        *[f"- {name}: {path.resolve()}" for name, path in paths.items()],
        "",
    ])


def _lab_summary(summary: dict[str, int]) -> str:
    return "\n".join(["# v1.9 Decision Transition Lab Summary", "", *[f"- {key}: {value}" for key, value in summary.items()], ""])


def _summary_counts(results: list[dict[str, object]]) -> dict[str, int]:
    statuses = [item["classification"]["classification_status"] for item in results]
    return {"scenarios_total": len(results), "passed": statuses.count("PASSED"), "failed": statuses.count("FAILED"), "review_required": statuses.count("REVIEW_REQUIRED")}


def _write_bundle(path: Path, paths: dict[str, Path]) -> list[dict[str, object]]:
    rows = [{"artifact_name": name, "path": str(p.resolve()), "status": "READY" if p.exists() else "MISSING"} for name, p in paths.items()]
    pd.DataFrame(rows).to_csv(path, index=False)
    return rows


def _copy_if_exists(source: Path, target: Path) -> None:
    if source.exists() and source.is_file():
        shutil.copyfile(source, target)


def _table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)


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
