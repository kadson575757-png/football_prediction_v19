# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from scripts.run_v19_final_pipeline_preview import run_v19_final_pipeline_preview
ROOT = Path(__file__).resolve().parents[1]
def test_raw_intake_to_batch_os_demo_uses_final_pipeline(tmp_path: Path) -> None:
    r = run_v19_final_pipeline_preview(raw_input_dir=ROOT / "tests/fixtures/raw_evidence_intake", output_dir=tmp_path / "raw_demo", emit_all=True, base_dir=ROOT)
    assert r["input_mode"] == "RAW_EVIDENCE"
    assert r["batch_os_status"] == "V19_BATCH_OS_PREVIEW_READY"
    assert Path(r["final_dashboard_path"]).exists()
