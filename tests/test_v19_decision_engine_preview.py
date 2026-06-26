# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.run_match_analysis_preview import run_match_analysis_preview


ROOT = Path(__file__).resolve().parents[1]
BASE_INTAKE = ROOT / "data" / "manual" / "real_match_intake.csv"
COMPLETION_FIXTURE = ROOT / "tests" / "fixtures" / "manual_evidence_completion" / "lazio_atalanta_completion.csv"


def test_v19_decision_engine_and_report_preview(tmp_path: Path) -> None:
    result = run_match_analysis_preview(
        real_match_intake=BASE_INTAKE,
        manual_evidence_completion=COMPLETION_FIXTURE,
        emit_v19_final_analysis_report=True,
        emit_v19_decision_report=True,
        emit_v19_recommendation_preview=True,
        base_dir=tmp_path,
    )

    assert result["v19_decision_engine_preview_status"] == "V19_DECISION_ENGINE_PREVIEW_READY"
    assert int(result["evidence_readiness_score"]) > 0
    assert result["final_decision_preview"] in {"ANALYST_LEAN_ONLY", "NO_BET_RECOMMENDED"}
    assert "Atalanta structural edge" in str(result["strongest_analyst_lean"])
    assert bool(result["recommendation_preview_enabled"])

    edges = pd.read_csv(result["structural_edges_output_path"], keep_default_na=False)
    assert "Atalanta attacking production edge" in " | ".join(edges["edge"].astype(str))
    assert "Lazio set-piece edge" in " | ".join(edges["edge"].astype(str))

    no_bet = pd.read_csv(result["no_bet_matrix_output_path"], keep_default_na=False)
    assert not no_bet.empty
    assert "Safety disabled productive betting" in " | ".join(no_bet["check"].astype(str))

    score_tree = pd.read_csv(result["score_tree_output_path"], keep_default_na=False)
    branches = set(score_tree["branch"].astype(str))
    assert {"Balanced", "Atalanta production", "Lazio set-piece"}.issubset(branches)

    assert result["v19_decision_report_status"] == "V19_DECISION_REPORT_PREVIEW_READY"
    report_path = Path(str(result["v19_decision_report_path"]))
    assert report_path.exists()
    report = report_path.read_text(encoding="utf-8")
    for phrase in [
        "Evidence Readiness",
        "Structural Edge Map",
        "Market Family Recommendation Preview",
        "No-Bet Matrix",
        "Score Tree",
        "Final Analyst Decision",
        "Atalanta has the strongest structural edge",
        "Lazio has real counterweights",
        "Recommendation Preview only",
        "Not betting advice",
        "No stake",
        "No ROI",
    ]:
        assert phrase in report

    assert not bool(result["network_calls_enabled"])
    assert not bool(result["betting_logic_enabled"])
    assert not bool(result["staking_logic_enabled"])
    assert not bool(result["roi_logic_enabled"])
