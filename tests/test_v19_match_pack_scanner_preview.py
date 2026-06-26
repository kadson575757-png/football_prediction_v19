# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.scan_v19_match_packs_preview import scan_v19_match_packs_preview

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "match_packs" / "match_pack_manifest.csv"


def test_match_pack_scanner_reads_manifest_and_writes_outputs(tmp_path: Path) -> None:
    result = scan_v19_match_packs_preview(manifest=MANIFEST, output_dir=tmp_path / "scan", emit_all=True, base_dir=ROOT)

    assert result["match_pack_scan_status"] == "V19_MATCH_PACK_SCAN_PREVIEW_READY"
    assert int(result["packs_total"]) >= 3
    assert Path(result["match_pack_scan_dashboard_path"]).exists()
    assert Path(result["match_pack_registry_path"]).exists()
    assert Path(result["match_pack_registry_md_path"]).exists()
    assert Path(result["match_pack_validation_results_json_path"]).exists()
    assert Path(result["match_pack_validation_results_csv_path"]).exists()
    assert result["network_calls_enabled"] is False
    assert result["betting_logic_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False

    registry = pd.read_csv(result["match_pack_registry_path"], keep_default_na=False)
    assert "lazio_atalanta_2026_02_14" in set(registry["match_id"])
    assert registry["synthetic_demo_pack"].astype(str).str.lower().eq("true").any()
    payload = json.loads(Path(result["match_pack_validation_results_json_path"]).read_text(encoding="utf-8"))
    assert payload["safety"]["network_calls_enabled"] is False
