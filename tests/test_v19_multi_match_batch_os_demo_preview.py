# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

from scripts.run_v19_multi_match_batch_os_demo_preview import run_v19_multi_match_batch_os_demo_preview

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "match_packs" / "match_pack_manifest.csv"


def test_multi_match_batch_os_demo_runs_end_to_end(tmp_path: Path) -> None:
    result = run_v19_multi_match_batch_os_demo_preview(manifest=MANIFEST, output_dir=tmp_path / "demo", emit_all=True, base_dir=ROOT)

    assert result["multi_match_demo_status"] == "V19_MULTI_MATCH_BATCH_OS_DEMO_READY"
    assert result["match_pack_scan_status"] == "V19_MATCH_PACK_SCAN_PREVIEW_READY"
    assert result["batch_health_gate_status"] == "V19_BATCH_HEALTH_GATE_PREVIEW_READY"
    assert result["batch_os_status"] == "V19_BATCH_OS_PREVIEW_READY"
    assert int(result["packs_total"]) >= 3
    assert int(result["auto_batch_matches_included"]) >= 1
    assert int(result["matches_total"]) >= 1
    assert result["network_calls_enabled"] is False
    assert result["prediction_logic_enabled"] is False
    assert result["betting_logic_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False

    out = tmp_path / "demo"
    for name in [
        "multi_match_demo_dashboard.md",
        "auto_batch_config.csv",
        "evidence_coverage_matrix.md",
        "batch_health_gate_report.md",
        "batch_os_results.json",
        "multi_match_demo_results.json",
        "multi_match_demo_bundle_index.csv",
    ]:
        assert (out / name).exists()

    payload = json.loads((out / "multi_match_demo_results.json").read_text(encoding="utf-8"))
    assert payload["multi_match_demo_status"] == "V19_MULTI_MATCH_BATCH_OS_DEMO_READY"
    dashboard = (out / "multi_match_demo_dashboard.md").read_text(encoding="utf-8")
    assert "What To Fix Before Real Multi-Match Use" in dashboard
    assert "No production betting. No stake. No ROI. No automatic betting." in dashboard
