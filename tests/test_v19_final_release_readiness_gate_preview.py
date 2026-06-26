# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from scripts.run_v19_final_pipeline_preview import run_v19_final_pipeline_preview
from scripts.run_v19_final_release_readiness_gate_preview import run_v19_final_release_readiness_gate_preview

ROOT = Path(__file__).resolve().parents[1]


def test_release_readiness_gate_ready_and_blocked_paths(tmp_path: Path) -> None:
    pipeline = run_v19_final_pipeline_preview(batch_config=ROOT / "tests/fixtures/batch_workbench/lazio_atalanta_batch_config.csv", output_dir=tmp_path / "final", emit_all=True, base_dir=ROOT)
    ready = run_v19_final_release_readiness_gate_preview(final_pipeline_results_json=pipeline["final_pipeline_results_json_path"], output_dir=tmp_path / "gate")
    assert ready["final_release_readiness_status"] == "V19_RELEASE_CANDIDATE_READY"
    assert ready["safety"]["network_calls_enabled"] is False

    broken = tmp_path / "broken.json"
    broken.write_text("{}", encoding="utf-8")
    blocked = run_v19_final_release_readiness_gate_preview(final_pipeline_results_json=broken, output_dir=tmp_path / "blocked")
    assert blocked["checks_failed"] > 0
    assert blocked["safety"]["betting_logic_enabled"] is False
