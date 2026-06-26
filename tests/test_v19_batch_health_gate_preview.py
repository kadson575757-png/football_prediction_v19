# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

from scripts.run_v19_batch_health_gate_preview import run_v19_batch_health_gate_preview
from scripts.scan_v19_match_packs_preview import scan_v19_match_packs_preview

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "match_packs" / "match_pack_manifest.csv"


def test_batch_health_gate_reads_validation_json_and_reports_status(tmp_path: Path) -> None:
    scan = scan_v19_match_packs_preview(manifest=MANIFEST, output_dir=tmp_path / "scan", emit_all=True, base_dir=ROOT)
    result = run_v19_batch_health_gate_preview(validation_json=scan["match_pack_validation_results_json_path"], output_dir=tmp_path / "health", emit_all=True, base_dir=ROOT)

    assert result["batch_health_gate_status"] == "V19_BATCH_HEALTH_GATE_PREVIEW_READY"
    assert result["batch_health_status"] in {"READY", "PARTIAL_READY", "BLOCKED", "INVALID"}
    assert result["can_run_batch_os"] is True
    assert result["can_run_completion_campaign"] is True
    assert result["can_run_portfolio_delta"] is True
    assert Path(result["batch_health_gate_report_path"]).exists()
    assert Path(result["batch_health_gate_result_json_path"]).exists()
    assert Path(result["batch_health_gate_matrix_path"]).exists()
    assert result["network_calls_enabled"] is False
    assert result["betting_logic_enabled"] is False

    payload = json.loads(Path(result["batch_health_gate_result_json_path"]).read_text(encoding="utf-8"))
    assert payload["safety"]["staking_logic_enabled"] is False
    assert payload["safety"]["roi_logic_enabled"] is False
