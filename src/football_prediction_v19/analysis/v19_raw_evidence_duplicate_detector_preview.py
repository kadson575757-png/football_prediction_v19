# -*- coding: utf-8 -*-
"""Duplicate detector for local raw evidence preview."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

V19_RAW_EVIDENCE_DUPLICATE_DETECTOR_PREVIEW_READY = "V19_RAW_EVIDENCE_DUPLICATE_DETECTOR_PREVIEW_READY"


def detect_raw_evidence_duplicates(classification_csv: str | Path, output_dir: str | Path) -> dict[str, object]:
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(classification_csv, keep_default_na=False)
    duplicates = frame[frame.duplicated(["raw_group_id", "file_name"], keep=False)] if not frame.empty else pd.DataFrame()
    csv_path = out / "duplicate_file_report.csv"
    md_path = out / "duplicate_file_report.md"
    duplicates.to_csv(csv_path, index=False)
    md_path.write_text("# v1.9 Duplicate File Report\n\n" + ("No duplicate files detected.\n" if duplicates.empty else duplicates.to_markdown(index=False)), encoding="utf-8")
    return {"duplicate_detector_status": V19_RAW_EVIDENCE_DUPLICATE_DETECTOR_PREVIEW_READY, "duplicate_files_count": len(duplicates), "duplicate_file_report_path": str(md_path), "duplicate_file_report_csv_path": str(csv_path), "network_calls_enabled": False, "prediction_logic_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}
