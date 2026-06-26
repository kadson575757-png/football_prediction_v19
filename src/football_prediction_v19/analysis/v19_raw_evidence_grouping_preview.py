# -*- coding: utf-8 -*-
"""Group classified raw evidence files by match-like raw folder."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

V19_RAW_EVIDENCE_GROUPING_PREVIEW_READY = "V19_RAW_EVIDENCE_GROUPING_PREVIEW_READY"


def group_raw_evidence_files(classification_csv: str | Path, output_dir: str | Path) -> dict[str, object]:
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(classification_csv, keep_default_na=False)
    rows = []
    for group_id, group in frame.groupby("raw_group_id"):
        rows.append({
            "raw_group_id": group_id,
            "files_count": len(group),
            "roles": " | ".join(sorted(set(group["file_role"]))),
            "synthetic_demo_pack": str(group["synthetic_demo_pack"].astype(str).str.lower().eq("true").any()).lower(),
            "not_real_match_data": str(group["not_real_match_data"].astype(str).str.lower().eq("true").any()).lower(),
            "not_for_prediction": str(group["not_for_prediction"].astype(str).str.lower().eq("true").any()).lower(),
        })
    groups = pd.DataFrame(rows)
    csv_path = out / "raw_evidence_groups.csv"
    md_path = out / "raw_evidence_grouping_report.md"
    groups.to_csv(csv_path, index=False)
    md_path.write_text("# v1.9 Raw Evidence Grouping Report\n\n" + _table(groups) + "\n", encoding="utf-8")
    return {"raw_evidence_grouping_status": V19_RAW_EVIDENCE_GROUPING_PREVIEW_READY, "raw_groups_total": len(rows), "raw_evidence_groups_path": str(csv_path), "raw_evidence_grouping_report_path": str(md_path), "network_calls_enabled": False, "prediction_logic_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}


def _table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)
