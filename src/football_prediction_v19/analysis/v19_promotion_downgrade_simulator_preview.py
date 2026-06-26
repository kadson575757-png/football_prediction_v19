# -*- coding: utf-8 -*-
"""Conditional promotion/downgrade simulator for the v1.9 workbench preview."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

V19_PROMOTION_DOWNGRADE_SIMULATION_PREVIEW_READY = "V19_PROMOTION_DOWNGRADE_SIMULATION_PREVIEW_READY"


@dataclass(frozen=True)
class V19PromotionDowngradeSimulatorConfig:
    final_decision_class: str = "ANALYST_LEAN_ONLY"
    conflict_score: str = "HIGH"
    output_dir: str | Path = "outputs/analysis_preview/v19_match_workbench"
    base_dir: str | Path = "."


@dataclass(frozen=True)
class V19PromotionDowngradeSimulatorResult:
    promotion_downgrade_simulation_status: str
    promotion_downgrade_simulation_path: str
    promotion_downgrade_simulation_json_path: str
    scenarios_count: int
    network_calls_enabled: bool
    betting_logic_enabled: bool
    staking_logic_enabled: bool
    roi_logic_enabled: bool
    recommendation: str


class V19PromotionDowngradeSimulator:
    def __init__(self, config: V19PromotionDowngradeSimulatorConfig) -> None:
        self.config = config
        self.base = Path(config.base_dir).resolve()

    def run(self) -> V19PromotionDowngradeSimulatorResult:
        out = _resolve(self.config.output_dir, self.base)
        out.mkdir(parents=True, exist_ok=True)
        scenarios = _scenarios(self.config.final_decision_class, self.config.conflict_score)
        md_path = out / "promotion_downgrade_simulation.md"
        json_path = out / "promotion_downgrade_simulation.json"
        md_path.write_text(_render(scenarios), encoding="utf-8")
        json_path.write_text(json.dumps({"scenarios": scenarios, "safety": _safety()}, indent=2), encoding="utf-8")
        return V19PromotionDowngradeSimulatorResult(
            V19_PROMOTION_DOWNGRADE_SIMULATION_PREVIEW_READY,
            str(md_path.resolve()),
            str(json_path.resolve()),
            len(scenarios),
            False,
            False,
            False,
            False,
            V19_PROMOTION_DOWNGRADE_SIMULATION_PREVIEW_READY,
        )


def _scenarios(final_class: str, conflict_score: str) -> list[dict[str, object]]:
    safety = "Preview only; no invented values, no stake, no ROI, no automatic betting."
    return [
        {
            "scenario_name": "Current State",
            "fields_added": "none",
            "expected_gate_change": "No change; critical blockers remain active.",
            "possible_final_class": final_class,
            "market_families_affected": "1X2 | Double Chance | DNB | Over/Under | BTTS | Score Family",
            "upgrade_conditions": "Add recent form, big chances, full availability and market movement.",
            "downgrade_risks": "Contradictory form, absences or adverse market movement.",
            "safety_statement": safety,
        },
        {
            "scenario_name": "Add Recent Form only",
            "fields_added": "recent form xG/goals for and against",
            "expected_gate_change": "Recent Form blocker reduced, but Big Chances, Availability and Market still block.",
            "possible_final_class": "ANALYST_LEAN_ONLY",
            "market_families_affected": "1X2 | Goals | Score Family",
            "upgrade_conditions": "If recent form supports Atalanta edge, confidence can rise conditionally.",
            "downgrade_risks": "If Lazio recent form is stronger, downgrade pressure increases.",
            "safety_statement": safety,
        },
        {
            "scenario_name": "Add Recent Form + Big Chances",
            "fields_added": "recent form plus big chances for/against",
            "expected_gate_change": "Chance-quality blockers can clear; market and availability still matter.",
            "possible_final_class": "BET_CANDIDATE_PREVIEW if edge aligns and conflict falls",
            "market_families_affected": "1X2 | Over/Under | BTTS | Score Family",
            "upgrade_conditions": "Atalanta form and big chances must align with structural edge.",
            "downgrade_risks": "Lazio chance-quality edge would move toward NO_BET_RECOMMENDED.",
            "safety_statement": safety,
        },
        {
            "scenario_name": "Add Full Availability",
            "fields_added": "goalkeeper, missing, suspended, doubtful and key absence fields",
            "expected_gate_change": "Lineup uncertainty resolves; still needs market movement.",
            "possible_final_class": "ANALYST_LEAN_ONLY or BET_CANDIDATE_PREVIEW",
            "market_families_affected": "1X2 | DNB | BTTS",
            "upgrade_conditions": "Atalanta attackers available and Lazio counterweights not strengthened.",
            "downgrade_risks": "Atalanta key attackers missing or goalkeeper risk.",
            "safety_statement": safety,
        },
        {
            "scenario_name": "Add Opening/Closing Odds",
            "fields_added": "opening, current and closing odds plus DNB/OU",
            "expected_gate_change": "Market alignment can be validated.",
            "possible_final_class": "BET_CANDIDATE_PREVIEW if no drift against Atalanta",
            "market_families_affected": "1X2 | Double Chance | DNB | Over/Under",
            "upgrade_conditions": "No market drift against Atalanta and no contradiction from DNB/OU.",
            "downgrade_risks": "Market drift against Atalanta raises conflict review.",
            "safety_statement": safety,
        },
        {
            "scenario_name": "All Critical Blockers Resolved",
            "fields_added": "recent form, big chances, full availability, opening/closing, DNB/OU",
            "expected_gate_change": "Critical blockers can clear; conflict score can drop from " + conflict_score + ".",
            "possible_final_class": "BET_CANDIDATE_PREVIEW or STRONG_BET_CANDIDATE_PREVIEW depending conflict_score and edge alignment",
            "market_families_affected": "all preview market families",
            "upgrade_conditions": "All added fields support Atalanta and do not strengthen Lazio counterweights.",
            "downgrade_risks": "Any contradiction keeps analyst lean or downgrades.",
            "safety_statement": safety,
        },
        {
            "scenario_name": "Downgrade Scenario",
            "fields_added": "contradictory recent form, availability and market movement",
            "expected_gate_change": "Contradictions override structural edge.",
            "possible_final_class": "NO_BET_RECOMMENDED or CONFLICT_REVIEW",
            "market_families_affected": "all preview market families",
            "upgrade_conditions": "none in this scenario",
            "downgrade_risks": "Lazio recent form stronger, Atalanta attackers missing, market drifts against Atalanta.",
            "safety_statement": safety,
        },
    ]


def _render(scenarios: list[dict[str, object]]) -> str:
    lines = ["# v1.9 Promotion/Downgrade Simulation Preview", ""]
    for scenario in scenarios:
        lines.extend([
            f"## {scenario['scenario_name']}",
            "",
            f"- fields_added: {scenario['fields_added']}",
            f"- expected_gate_change: {scenario['expected_gate_change']}",
            f"- possible_final_class: {scenario['possible_final_class']}",
            f"- market_families_affected: {scenario['market_families_affected']}",
            f"- upgrade_conditions: {scenario['upgrade_conditions']}",
            f"- downgrade_risks: {scenario['downgrade_risks']}",
            f"- safety_statement: {scenario['safety_statement']}",
            "",
        ])
    return "\n".join(lines)


def _safety() -> dict[str, bool]:
    return {"network_calls_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}


def _resolve(path: str | Path, base: Path) -> Path:
    p = Path(path)
    return (base / p).resolve() if not p.is_absolute() else p.resolve()
