# -*- coding: utf-8 -*-
"""Evidence fix plan preview."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

V19_EVIDENCE_FIX_PLAN_PREVIEW_READY = "V19_EVIDENCE_FIX_PLAN_PREVIEW_READY"


def write_evidence_fix_plan(validation_csv: str | Path, output_dir: str | Path) -> dict[str, object]:
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(validation_csv, keep_default_na=False)
    rows = []
    for _, row in frame.iterrows():
        rows.append({"match_id": row.get("match_id", ""), "health_status": row.get("health_status", ""), "next_action": row.get("warnings", "") or row.get("errors", "") or "Ready for batch OS"})
    plan = pd.DataFrame(rows)
    csv_path = out / "evidence_fix_plan.csv"
    md_path = out / "evidence_fix_plan.md"
    plan.to_csv(csv_path, index=False)
    md_path.write_text("# v1.9 Evidence Fix Plan\n\n" + _table(plan) + "\n", encoding="utf-8")
    return {"evidence_fix_plan_status": V19_EVIDENCE_FIX_PLAN_PREVIEW_READY, "evidence_fix_plan_path": str(md_path), "evidence_fix_plan_csv_path": str(csv_path), "network_calls_enabled": False, "prediction_logic_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}


def _table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)
