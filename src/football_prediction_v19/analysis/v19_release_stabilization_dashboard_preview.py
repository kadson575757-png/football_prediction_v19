# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
import pandas as pd


def write_release_stabilization_dashboard(output_path: str | Path, results: list[dict[str, object]], acceptance: dict[str, object]) -> str:
    path = Path(output_path); path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(results)
    ready = acceptance.get("final_acceptance_status") == "V19_FINAL_ACCEPTANCE_PASSED"
    text = "\n".join(["# v1.9 Release Stabilization Dashboard", "", "## 1. Stabilization Status", "- v19_release_stabilization_status: V19_RELEASE_STABILIZATION_READY", f"- final_acceptance_status: {acceptance.get('final_acceptance_status')}", f"- recommendation: {acceptance.get('recommendation')}", "", "## 2. Checks Run", "- Safety Invariant Scan", "- Output Hygiene Guard", "- CLI Command Validation", "- Docs Consistency Check", "- Final Acceptance Gate", "", "## 3. Results Matrix", _table(frame), "", "## 4. Final Acceptance", str(acceptance.get("final_acceptance_status")), "", "## 5. Ready To Tag Preview?", "yes" if ready else "no", "", "## 6. What To Do Next", "- pull main", "- run smoke tests", "- review docs", "- optionally create tag", "", "## 7. Safety Footer", "No production betting. No stake. No ROI. No automatic betting.", ""])
    path.write_text(text, encoding="utf-8")
    return str(path.resolve())


def _table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)
