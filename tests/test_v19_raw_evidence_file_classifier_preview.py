# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from football_prediction_v19.analysis.v19_raw_evidence_file_classifier_preview import classify_raw_evidence_files
ROOT = Path(__file__).resolve().parents[1]
def test_raw_evidence_classifier_writes_outputs(tmp_path: Path) -> None:
    r = classify_raw_evidence_files(ROOT / "tests/fixtures/raw_evidence_intake", tmp_path)
    assert r["raw_file_classification_status"] == "V19_RAW_EVIDENCE_FILE_CLASSIFIER_PREVIEW_READY"
    assert r["files_total"] >= 3
    assert Path(r["raw_file_classification_path"]).exists()
    assert r["network_calls_enabled"] is False
