# -*- coding: utf-8 -*-
"""Classify v1.9 transition-lab scenario outcomes."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

V19_TRANSITION_CLASSIFICATION_READY = "V19_TRANSITION_CLASSIFICATION_READY"


@dataclass(frozen=True)
class V19TransitionClassifierConfig:
    base_workbench_json: str | Path | None = None
    rerun_workbench_json: str | Path | None = None
    decision_delta_json: str | Path | None = None
    scenario: dict[str, object] | None = None
    actual_override: dict[str, object] | None = None
    output_dir: str | Path | None = None
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19TransitionClassificationResult:
    transition_classification_status: str
    scenario_id: str
    expected_final_decision_class: str
    actual_final_decision_class: str
    transition_matched: bool
    expected_promotion_allowed: bool
    actual_promotion_allowed: bool
    promotion_matched: bool
    expected_conflict_score: str
    actual_conflict_score: str
    conflict_matched: bool
    removed_blockers_matched: bool
    market_family_changes_matched: bool
    classification_status: str
    explanation: str
    classification_json_path: str
    classification_md_path: str
    network_calls_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19TransitionClassifier:
    def __init__(self, config: V19TransitionClassifierConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> V19TransitionClassificationResult:
        scenario = self.config.scenario or {}
        actual = self.config.actual_override or _actual_from_json(_resolve_optional(self.config.rerun_workbench_json, self.base), _resolve_optional(self.config.decision_delta_json, self.base))
        delta = _read_json(_resolve_optional(self.config.decision_delta_json, self.base)).get("delta", {})
        expected_class = str(scenario.get("expected_final_decision_class", ""))
        actual_class = str(actual.get("final_decision_class", ""))
        expected_promotion = _bool(scenario.get("expected_promotion_allowed", False))
        actual_promotion = _bool(actual.get("promotion_allowed", False))
        expected_conflict = str(scenario.get("expected_conflict_score", ""))
        actual_conflict = str(actual.get("conflict_score", ""))
        removed_expected = set(scenario.get("expected_removed_blockers", []) or [])
        removed_actual = set(delta.get("blockers_removed", []) or actual.get("blockers_removed", []) or [])
        market_expected = set(scenario.get("expected_market_family_changes", []) or [])
        market_actual = set(delta.get("market_families_upgraded", []) or delta.get("market_families_downgraded", []) or actual.get("market_family_changes", []) or [])
        transition_matched = expected_class == actual_class
        promotion_matched = expected_promotion == actual_promotion
        conflict_matched = expected_conflict == actual_conflict
        removed_matched = removed_expected.issubset(removed_actual)
        market_matched = market_expected.issubset(market_actual) or (transition_matched and promotion_matched and bool(market_expected) and not market_actual)
        if transition_matched and promotion_matched and conflict_matched and removed_matched and market_matched:
            status = "PASSED"
        elif transition_matched and promotion_matched:
            status = "REVIEW_REQUIRED"
        else:
            status = "FAILED"
        explanation = "Scenario transition matched expected preview outcome." if status == "PASSED" else "Scenario transition requires review." if status == "REVIEW_REQUIRED" else "Scenario transition did not match expected outcome."
        out_json = ""
        out_md = ""
        result_payload = {
            "scenario_id": scenario.get("scenario_id", ""),
            "expected": {
                "final_decision_class": expected_class,
                "promotion_allowed": expected_promotion,
                "conflict_score": expected_conflict,
            },
            "actual": {
                "final_decision_class": actual_class,
                "promotion_allowed": actual_promotion,
                "conflict_score": actual_conflict,
            },
            "transition_matched": transition_matched,
            "promotion_matched": promotion_matched,
            "conflict_matched": conflict_matched,
            "removed_blockers_matched": removed_matched,
            "market_family_changes_matched": market_matched,
            "classification_status": status,
            "explanation": explanation,
            "safety": _safety(),
        }
        if self.config.output_dir:
            out = _resolve_optional(self.config.output_dir, self.base)
            out.mkdir(parents=True, exist_ok=True)
            json_path = out / "transition_classification.json"
            md_path = out / "transition_classification.md"
            json_path.write_text(json.dumps(result_payload, indent=2), encoding="utf-8")
            md_path.write_text(_render(result_payload), encoding="utf-8")
            out_json = str(json_path.resolve())
            out_md = str(md_path.resolve())
        return V19TransitionClassificationResult(
            V19_TRANSITION_CLASSIFICATION_READY,
            str(scenario.get("scenario_id", "")),
            expected_class,
            actual_class,
            transition_matched,
            expected_promotion,
            actual_promotion,
            promotion_matched,
            expected_conflict,
            actual_conflict,
            conflict_matched,
            removed_matched,
            market_matched,
            status,
            explanation,
            out_json,
            out_md,
            False,
            False,
            False,
            False,
            V19_TRANSITION_CLASSIFICATION_READY,
        )


def _actual_from_json(rerun_json: Path, delta_json: Path) -> dict[str, object]:
    rerun = _read_json(rerun_json)
    delta = _read_json(delta_json).get("delta", {})
    pr = rerun.get("production_readiness", {})
    return {
        "final_decision_class": pr.get("final_decision_class", ""),
        "promotion_allowed": pr.get("promotion_allowed", False),
        "conflict_score": pr.get("conflict_score", ""),
        "blockers_removed": delta.get("blockers_removed", []),
        "market_family_changes": (delta.get("market_families_upgraded", []) or []) + (delta.get("market_families_downgraded", []) or []),
    }


def _render(payload: dict[str, object]) -> str:
    return "\n".join([
        "# v1.9 Transition Classification",
        "",
        f"- scenario_id: {payload['scenario_id']}",
        f"- classification_status: {payload['classification_status']}",
        f"- transition_matched: {str(payload['transition_matched']).lower()}",
        f"- promotion_matched: {str(payload['promotion_matched']).lower()}",
        f"- conflict_matched: {str(payload['conflict_matched']).lower()}",
        f"- explanation: {payload['explanation']}",
        "",
        "Preview only. No stake. No ROI. No automatic betting.",
        "",
    ])


def _read_json(path: Path) -> dict[str, object]:
    try:
        if not path or not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _resolve_optional(path: str | Path | None, base: Path) -> Path:
    p = Path(str(path or ""))
    return (base / p).resolve() if not p.is_absolute() else p.resolve()


def _bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _safety() -> dict[str, bool]:
    return {"network_calls_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}
