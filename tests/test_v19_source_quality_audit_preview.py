# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from football_prediction_v19.analysis.v19_raw_evidence_file_classifier_preview import classify_raw_evidence_files
from football_prediction_v19.analysis.v19_source_quality_audit_preview import audit_source_quality
ROOT = Path(__file__).resolve().parents[1]
def test_source_quality_audit_writes_report(tmp_path: Path) -> None:
    c = classify_raw_evidence_files(ROOT / "tests/fixtures/raw_evidence_intake", tmp_path / "classify")
    r = audit_source_quality(c["raw_file_classification_path"], tmp_path / "quality")
    assert r["source_quality_status"] == "V19_SOURCE_QUALITY_AUDIT_PREVIEW_READY"
    assert Path(r["source_quality_report_path"]).exists()
    assert r["betting_logic_enabled"] is False
