# -*- coding: utf-8 -*-
"""Source quality audit for local raw evidence preview."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

V19_SOURCE_QUALITY_AUDIT_PREVIEW_READY = "V19_SOURCE_QUALITY_AUDIT_PREVIEW_READY"


def audit_source_quality(classification_csv: str | Path, output_dir: str | Path) -> dict[str, object]:
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(classification_csv, keep_default_na=False)
    unknown = int(frame["file_role"].eq("UNKNOWN_EVIDENCE").sum()) if not frame.empty else 0
    score = max(0, 100 - unknown * 15)
    result = {"source_quality_status": V19_SOURCE_QUALITY_AUDIT_PREVIEW_READY, "files_total": len(frame), "unknown_files": unknown, "source_quality_score": score, "source_quality_label": "READY" if unknown == 0 else "NEEDS_REVIEW", "safety": _safety()}
    json_path = out / "source_quality_scores.json"
    md_path = out / "source_quality_report.md"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    md_path.write_text(f"# v1.9 Source Quality Report\n\n- source_quality_label: {result['source_quality_label']}\n- unknown_files: {unknown}\n- source_quality_score: {score}\n", encoding="utf-8")
    return {**result, "source_quality_scores_path": str(json_path), "source_quality_report_path": str(md_path), **_safety()}


def _safety() -> dict[str, bool]:
    return {"network_calls_enabled": False, "prediction_logic_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}
