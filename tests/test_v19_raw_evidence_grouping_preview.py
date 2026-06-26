# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from football_prediction_v19.analysis.v19_raw_evidence_file_classifier_preview import classify_raw_evidence_files
from football_prediction_v19.analysis.v19_raw_evidence_grouping_preview import group_raw_evidence_files
ROOT = Path(__file__).resolve().parents[1]
def test_raw_evidence_grouping_writes_group_report(tmp_path: Path) -> None:
    c = classify_raw_evidence_files(ROOT / "tests/fixtures/raw_evidence_intake", tmp_path / "classify")
    r = group_raw_evidence_files(c["raw_file_classification_path"], tmp_path / "group")
    assert r["raw_evidence_grouping_status"] == "V19_RAW_EVIDENCE_GROUPING_PREVIEW_READY"
    assert r["raw_groups_total"] >= 3
    assert Path(r["raw_evidence_grouping_report_path"]).exists()
