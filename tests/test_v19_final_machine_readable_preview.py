# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from pathlib import Path
from scripts.run_v19_final_pipeline_preview import run_v19_final_pipeline_preview

ROOT = Path(__file__).resolve().parents[1]


def test_final_machine_json_contains_major_sections_and_safety(tmp_path: Path) -> None:
    result = run_v19_final_pipeline_preview(batch_config=ROOT / "tests/fixtures/batch_workbench/lazio_atalanta_batch_config.csv", output_dir=tmp_path / "final", emit_all=True, base_dir=ROOT)
    payload = json.loads(Path(result["final_pipeline_results_json_path"]).read_text(encoding="utf-8"))
    for section in ["release_readiness", "raw_intake", "match_pack_scan", "batch_health_gate", "batch_os", "completion_campaign", "completion_rerun", "portfolio_delta", "scenario_lab", "smoke_tests", "artifact_paths"]:
        assert section in payload
    assert payload["safety"]["network_calls_enabled"] is False
    assert payload["safety"]["prediction_logic_enabled"] is False
    assert payload["safety"]["betting_logic_enabled"] is False
    assert payload["safety"]["staking_logic_enabled"] is False
    assert payload["safety"]["roi_logic_enabled"] is False
    assert payload["safety"]["v19_release_candidate_enabled"] is True
