# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from pathlib import Path
from scripts.run_v19_final_pipeline_preview import run_v19_final_pipeline_preview

ROOT = Path(__file__).resolve().parents[1]


def test_final_pipeline_batch_config_mode_creates_dashboard_json_and_safety(tmp_path: Path) -> None:
    result = run_v19_final_pipeline_preview(batch_config=ROOT / "tests/fixtures/batch_workbench/lazio_atalanta_batch_config.csv", output_dir=tmp_path / "final", emit_all=True, base_dir=ROOT)
    assert result["v19_final_pipeline_status"] == "V19_FINAL_PIPELINE_PREVIEW_READY"
    assert result["batch_os_status"] == "V19_BATCH_OS_PREVIEW_READY"
    assert result["final_release_readiness_status"] == "V19_RELEASE_CANDIDATE_READY"
    assert Path(result["final_dashboard_path"]).exists()
    assert Path(result["final_pipeline_results_json_path"]).exists()
    assert result["network_calls_enabled"] is False
    payload = json.loads(Path(result["final_pipeline_results_json_path"]).read_text(encoding="utf-8"))
    assert payload["safety"]["v19_release_candidate_enabled"] is True
    assert payload["safety"]["betting_logic_enabled"] is False
