# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from football_prediction_v19.analysis.v19_release_stabilization_preview import run_release_stabilization
ROOT = Path(__file__).resolve().parents[1]


def test_release_stabilization_runner_creates_acceptance_outputs(tmp_path: Path) -> None:
    result = run_release_stabilization(tmp_path / "stabilize", emit_all=True, repo_root=ROOT)
    assert result["v19_release_stabilization_status"] == "V19_RELEASE_STABILIZATION_READY"
    assert result["final_acceptance_status"] == "V19_FINAL_ACCEPTANCE_PASSED"
    assert result["recommendation"] == "V19_READY_TO_TAG_PREVIEW"
    assert result["network_calls_enabled"] is False
    assert result["automatic_betting_enabled"] is False
    assert Path(result["release_stabilization_dashboard_path"]).exists()
    assert Path(tmp_path / "stabilize" / "final_acceptance_report.md").exists()
    assert Path(result["release_stabilization_results_json_path"]).exists()
