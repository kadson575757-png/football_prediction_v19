# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from football_prediction_v19.analysis.v19_raw_evidence_duplicate_detector_preview import detect_raw_evidence_duplicates
from football_prediction_v19.analysis.v19_raw_evidence_file_classifier_preview import classify_raw_evidence_files
ROOT = Path(__file__).resolve().parents[1]
def test_raw_duplicate_detector_writes_report(tmp_path: Path) -> None:
    c = classify_raw_evidence_files(ROOT / "tests/fixtures/raw_evidence_intake", tmp_path / "classify")
    r = detect_raw_evidence_duplicates(c["raw_file_classification_path"], tmp_path / "dupes")
    assert r["duplicate_detector_status"] == "V19_RAW_EVIDENCE_DUPLICATE_DETECTOR_PREVIEW_READY"
    assert Path(r["duplicate_file_report_path"]).exists()
