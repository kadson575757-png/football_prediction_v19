# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from football_prediction_v19.analysis.v19_evidence_fix_plan_preview import write_evidence_fix_plan
from scripts.scan_v19_match_packs_preview import scan_v19_match_packs_preview
ROOT = Path(__file__).resolve().parents[1]
def test_evidence_fix_plan_writes_next_actions(tmp_path: Path) -> None:
    scan = scan_v19_match_packs_preview(manifest=ROOT / "tests/fixtures/match_packs/match_pack_manifest.csv", output_dir=tmp_path / "scan", base_dir=ROOT)
    r = write_evidence_fix_plan(scan["match_pack_validation_results_csv_path"], tmp_path / "plan")
    assert r["evidence_fix_plan_status"] == "V19_EVIDENCE_FIX_PLAN_PREVIEW_READY"
    assert Path(r["evidence_fix_plan_path"]).exists()
