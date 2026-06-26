# -*- coding: utf-8 -*-
"""Final action plan renderer for v1.9 batch OS."""
from __future__ import annotations

from pathlib import Path


def write_final_action_plan(output_path: str | Path, *, master_template_path: str, batch_config: str) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join([
        "# v1.9 Final Action Plan",
        "",
        "## 1. Immediate Next Step",
        "Open master_completion_template.csv and fill only user_value.",
        "",
        "## 2. Highest Priority Fields",
        "- Recent Form",
        "- Big Chances",
        "- Availability",
        "- Opening/Closing Market",
        "- DNB/OU Market",
        "",
        "## 3. Per Match Next Actions",
        "| match_id | current decision class | missing groups | recommended next action | expected possible transition |",
        "| --- | --- | --- | --- | --- |",
        "| lazio_atalanta_2026_02_14 | ANALYST_LEAN_ONLY | Recent Form, Big Chances, Availability, Market | Fill critical fields | BET_CANDIDATE_PREVIEW if aligned |",
        "",
        "## 4. Rerun Command",
        f"`$PY scripts/run_v19_batch_completion_rerun_preview.py --base-batch-results-json outputs/analysis_preview/v19_batch_workbench/batch_results.json --filled-master-completion-csv {master_template_path} --batch-config {batch_config} --output-dir outputs/analysis_preview/v19_batch_completion_rerun --emit-all`",
        "",
        "## 5. Review Files After Rerun",
        "- portfolio_delta_dashboard.md",
        "- candidate_change_report.md",
        "- missing_data_progress_report.md",
        "",
        "## 6. Safety Reminder",
        "No stake, no ROI, no automatic betting.",
        "",
    ])
    path.write_text(text, encoding="utf-8")
    return str(path.resolve())
