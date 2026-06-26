# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

from scripts.run_match_analysis_preview import run_match_analysis_preview


ROOT = Path(__file__).resolve().parents[1]
BASE_INTAKE = ROOT / "data" / "manual" / "real_match_intake.csv"
COMPLETION_FIXTURE = ROOT / "tests" / "fixtures" / "manual_evidence_completion" / "lazio_atalanta_completion.csv"


def test_runner_emits_v19_final_analysis_report_from_manual_completion(tmp_path: Path) -> None:
    result = run_match_analysis_preview(
        real_match_intake=BASE_INTAKE,
        manual_evidence_completion=COMPLETION_FIXTURE,
        emit_v19_final_analysis_report=True,
        base_dir=tmp_path,
    )

    assert result["real_match_analysis_runner_status"] == "REAL_MATCH_ANALYSIS_RUNNER_PREVIEW_READY"
    assert result["v19_final_analysis_report_status"] == "V19_FINAL_ANALYSIS_REPORT_PREVIEW_READY"
    report_path = Path(str(result["report_output_path"]))
    assert report_path.exists()
    report = report_path.read_text(encoding="utf-8")

    assert "Kurzfazit" in report
    assert "Atalanta besitzt den stärkeren Angriffs" in report
    assert "Lazio Set-Piece" in report
    assert "Possession 50 - 50" in report
    assert "Shots 18 - 12" in report
    assert "Shots on Target 5 - 5" in report
    assert "Keine Recommendation" in report
    assert "No production recommendation" in report or "Kein produktiver Model Output" in report
    assert "Stake:" not in report
    assert "ROI:" not in report
    assert not bool(result["prediction_logic_enabled"])
    assert not bool(result["betting_logic_enabled"])
    assert not bool(result["staking_logic_enabled"])
    assert not bool(result["roi_logic_enabled"])
