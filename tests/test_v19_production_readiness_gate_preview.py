# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.run_v19_analysis_suite_preview import run_v19_analysis_suite_preview


ROOT = Path(__file__).resolve().parents[1]
BASE_INTAKE = ROOT / "data" / "manual" / "real_match_intake.csv"
COMPLETION_FIXTURE = ROOT / "tests" / "fixtures" / "manual_evidence_completion" / "lazio_atalanta_completion.csv"


def test_v19_production_readiness_gate_blocks_promotion_for_lazio_atalanta(tmp_path: Path) -> None:
    result = run_v19_analysis_suite_preview(
        real_match_intake_path=BASE_INTAKE,
        manual_evidence_completion_path=COMPLETION_FIXTURE,
        emit_all=True,
        base_dir=tmp_path,
    )

    assert result["v19_production_readiness_gate_status"] == "V19_PRODUCTION_READINESS_GATE_PREVIEW_READY"
    assert result["production_readiness_gate_enabled"] is True
    assert result["decision_promotion_preview_enabled"] is True
    assert result["recommendation_preview_enabled"] is True
    assert result["final_decision_class"] == "ANALYST_LEAN_ONLY"
    assert result["promotion_allowed"] is False
    assert result["strong_promotion_allowed"] is False
    assert result["conflict_score"] in {"HIGH", "MEDIUM_HIGH"}

    report_path = Path(str(result["production_readiness_report_path"]))
    assert report_path.exists()
    report = report_path.read_text(encoding="utf-8")
    for phrase in [
        "v1.9 Production Readiness Gate Preview",
        "Atalanta has the strongest structural edge",
        "Lazio has real counterweights through xGA, set pieces and shot volume",
        "Evidence readiness is high but not production-ready",
        "Critical blockers prevent promotion beyond analyst lean",
        "No production bet",
    ]:
        assert phrase in report

    gate_path = tmp_path / "outputs" / "analysis_preview" / "v19_production_readiness_gate" / "v19_production_readiness_gate.csv"
    gate = pd.read_csv(gate_path, keep_default_na=False).iloc[0].to_dict()
    assert int(gate["readiness_score"]) == 85
    assert int(gate["edge_score"]) > 0
    assert int(gate["counterweight_score"]) > 0
    for blocker in [
        "missing recent form",
        "missing big chances",
        "missing full availability details",
        "missing opening/closing odds",
    ]:
        assert blocker in gate["critical_blockers"]
    assert gate["upgrade_conditions"]
    assert gate["downgrade_conditions"]


def test_v19_suite_json_contains_production_readiness_and_safety(tmp_path: Path) -> None:
    result = run_v19_analysis_suite_preview(
        real_match_intake_path=BASE_INTAKE,
        manual_evidence_completion_path=COMPLETION_FIXTURE,
        emit_all=True,
        base_dir=tmp_path,
    )

    machine = json.loads(Path(str(result["machine_readable_decision_path"])).read_text(encoding="utf-8"))
    readiness = machine["production_readiness"]
    assert readiness["status"] == "V19_PRODUCTION_READINESS_GATE_PREVIEW_READY"
    assert readiness["final_decision_class"] == "ANALYST_LEAN_ONLY"
    assert readiness["promotion_allowed"] is False
    assert readiness["strong_promotion_allowed"] is False
    assert readiness["conflict_score"] in {"HIGH", "MEDIUM_HIGH"}
    assert readiness["critical_blockers"]
    assert machine["safety"]["production_readiness_gate_enabled"] is True
    assert machine["safety"]["network_calls_enabled"] is False
    assert machine["safety"]["betting_logic_enabled"] is False
    assert machine["safety"]["staking_logic_enabled"] is False
    assert machine["safety"]["roi_logic_enabled"] is False
