# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

from scripts.run_v19_analysis_suite_preview import run_v19_analysis_suite_preview


ROOT = Path(__file__).resolve().parents[1]
BASE_INTAKE = ROOT / "data" / "manual" / "real_match_intake.csv"
COMPLETION_FIXTURE = ROOT / "tests" / "fixtures" / "manual_evidence_completion" / "lazio_atalanta_completion.csv"


def test_v19_analysis_suite_creates_full_output_bundle(tmp_path: Path) -> None:
    result = run_v19_analysis_suite_preview(
        real_match_intake_path=BASE_INTAKE,
        manual_evidence_completion_path=COMPLETION_FIXTURE,
        emit_all=True,
        base_dir=tmp_path,
    )

    assert result["v19_analysis_suite_status"] == "V19_ANALYSIS_SUITE_PREVIEW_READY"
    out = Path(str(result["analysis_suite_output_dir"]))
    assert out.exists()
    expected = [
        "analysis_suite_summary.md",
        "final_decision_card.md",
        "full_match_analysis.md",
        "decision_report.md",
        "score_tree_detail.md",
        "market_family_matrix.md",
        "no_bet_matrix.md",
        "evidence_audit.md",
        "missing_data_action_plan.md",
        "production_readiness_report.md",
        "machine_readable_decision.json",
        "analysis_suite_bundle_index.csv",
    ]
    for name in expected:
        assert (out / name).exists()

    summary = (out / "analysis_suite_summary.md").read_text(encoding="utf-8")
    assert "v1.9 Analysis Suite" in summary
    assert "Atalanta has the strongest structural edge" in summary
    assert "Lazio has real counterweights" in summary
    assert "Final status" in summary
    assert "No production bet" in summary
    assert "Production Readiness" in summary
    assert "promotion_allowed=false" in summary

    card = (out / "final_decision_card.md").read_text(encoding="utf-8")
    for phrase in ["Final Decision Preview", "final_decision_class", "promotion_allowed: false", "Strongest Lean", "Counterweights", "Recommendation Preview only", "No stake", "No ROI"]:
        assert phrase in card

    score_tree = (out / "score_tree_detail.md").read_text(encoding="utf-8")
    for phrase in ["Low Scoring Branch", "Balanced Branch", "Atalanta Production Branch", "Lazio Set-Piece", "Draw / Chaos Branch", "No exact score prediction"]:
        assert phrase in score_tree

    market = (out / "market_family_matrix.md").read_text(encoding="utf-8")
    for phrase in ["1X2", "Double Chance", "DNB", "Over/Under", "BTTS", "Score Family", "No-Bet"]:
        assert phrase in market

    audit = (out / "evidence_audit.md").read_text(encoding="utf-8")
    for phrase in ["Team xG/xGA", "Player xG/xA", "Possession", "Shots", "Current Odds", "Missing Evidence", "Evidence-to-Decision Trace"]:
        assert phrase in audit

    plan = (out / "missing_data_action_plan.md").read_text(encoding="utf-8")
    for phrase in ["Priority 1 Critical", "recent 5 match xG", "big chances", "Full Availability", "opening/closing odds", "upgrade", "downgrade"]:
        assert phrase.lower() in plan.lower()

    machine = json.loads((out / "machine_readable_decision.json").read_text(encoding="utf-8"))
    assert machine["final_decision_preview"]
    assert "evidence_readiness_score" in machine
    assert machine["safety"]["network_calls_enabled"] is False
    assert machine["safety"]["betting_logic_enabled"] is False
    assert machine["safety"]["staking_logic_enabled"] is False
    assert machine["safety"]["roi_logic_enabled"] is False
    assert machine["safety"]["recommendation_preview_enabled"] is True
    assert machine["safety"]["production_readiness_gate_enabled"] is True
    assert machine["production_readiness"]["final_decision_class"] == "ANALYST_LEAN_ONLY"
    assert machine["production_readiness"]["promotion_allowed"] is False
    assert machine["production_readiness"]["strong_promotion_allowed"] is False
    assert machine["score_tree"]
    assert machine["market_family_read"]
    assert int(result["suite_artifacts_count"]) >= 12
    assert result["v19_production_readiness_gate_status"] == "V19_PRODUCTION_READINESS_GATE_PREVIEW_READY"
    assert result["production_readiness_gate_enabled"] is True
    assert result["decision_promotion_preview_enabled"] is True
    assert result["final_decision_class"] == "ANALYST_LEAN_ONLY"
    assert result["promotion_allowed"] is False
    assert result["strong_promotion_allowed"] is False
    assert result["conflict_score"] in {"HIGH", "MEDIUM_HIGH"}
