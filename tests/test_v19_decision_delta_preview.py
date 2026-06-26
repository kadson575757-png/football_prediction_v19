# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

from football_prediction_v19.analysis.v19_decision_delta_preview import V19DecisionDeltaConfig, V19DecisionDeltaRunner


def _workbench(path: Path, *, final_class: str, score: int, promotion: bool, blockers: list[str], family_status: str = "PARTIAL") -> Path:
    payload = {
        "match": {"home_team": "Lazio", "away_team": "Atalanta"},
        "production_readiness": {
            "final_decision_class": final_class,
            "readiness_score": score,
            "conflict_score": "HIGH" if blockers else "LOW",
            "promotion_allowed": promotion,
            "critical_blockers": blockers,
        },
        "analysis_suite": {
            "market_family_read": [
                {"market_family": "1X2", "status": family_status},
                {"market_family": "DNB", "status": "BLOCKED"},
            ]
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_decision_delta_detects_unchanged_decision(tmp_path: Path) -> None:
    base = _workbench(tmp_path / "base.json", final_class="ANALYST_LEAN_ONLY", score=85, promotion=False, blockers=["missing recent form"])
    rerun = _workbench(tmp_path / "rerun.json", final_class="ANALYST_LEAN_ONLY", score=85, promotion=False, blockers=["missing recent form"])
    result = V19DecisionDeltaRunner(V19DecisionDeltaConfig(base, rerun, output_dir=tmp_path)).run()
    assert result.decision_delta_status == "V19_DECISION_DELTA_PREVIEW_READY"
    assert result.decision_class_changed is False
    assert result.evidence_readiness_delta == 0
    assert result.promotion_changed is False


def test_decision_delta_detects_removed_blockers_and_promotion_change(tmp_path: Path) -> None:
    base = _workbench(tmp_path / "base.json", final_class="ANALYST_LEAN_ONLY", score=85, promotion=False, blockers=["missing recent form", "missing big chances"])
    rerun = _workbench(tmp_path / "rerun.json", final_class="BET_CANDIDATE_PREVIEW", score=92, promotion=True, blockers=[])
    result = V19DecisionDeltaRunner(V19DecisionDeltaConfig(base, rerun, filled_values_count=10, output_dir=tmp_path)).run()
    assert result.decision_class_changed is True
    assert result.evidence_readiness_delta == 7
    assert result.promotion_changed is True
    assert "missing recent form" in result.blockers_removed
    assert "missing big chances" in result.blockers_removed


def test_decision_delta_detects_market_family_upgrade_and_safety(tmp_path: Path) -> None:
    base = _workbench(tmp_path / "base.json", final_class="ANALYST_LEAN_ONLY", score=85, promotion=False, blockers=["missing recent form"], family_status="PARTIAL")
    rerun = _workbench(tmp_path / "rerun.json", final_class="BET_CANDIDATE_PREVIEW", score=90, promotion=True, blockers=[], family_status="READY")
    result = V19DecisionDeltaRunner(V19DecisionDeltaConfig(base, rerun, filled_values_count=5, output_dir=tmp_path)).run()
    assert "1X2" in result.market_families_upgraded
    assert result.staking_logic_enabled is False
    assert result.roi_logic_enabled is False
    report = Path(result.decision_delta_report_path).read_text(encoding="utf-8")
    assert "Safety Footer" in report
    assert "No stake" in report
