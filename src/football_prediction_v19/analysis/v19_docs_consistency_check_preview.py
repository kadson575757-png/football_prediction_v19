# -*- coding: utf-8 -*-
"""Docs consistency check for v1.9 release stabilization."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REQUIRED_DOCS = ["docs/v19_final_pipeline_user_guide.md", "docs/v19_release_candidate_scope.md", "docs/v19_safe_usage_notes.md", "docs/v19_commands.md"]
REQUIRED_PHRASES = ["no automatic betting", "no stake", "no roi", "no external network calls", "preview", "analyst decision", "raw evidence", "match pack", "batch config", "single match"]


def run_docs_consistency_check(output_dir: str | Path, *, repo_root: str | Path = ".") -> dict[str, object]:
    root = Path(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    text = ""
    rows = []
    for doc in REQUIRED_DOCS:
        path = root / doc
        exists = path.exists()
        content = path.read_text(encoding="utf-8").lower() if exists else ""
        text += "\n" + content
        rows.append({"item": doc, "kind": "doc_exists", "status": "PASSED" if exists else "FAILED"})
    for phrase in REQUIRED_PHRASES:
        rows.append({"item": phrase, "kind": "required_phrase", "status": "PASSED" if phrase in text else "FAILED"})
    failed = [row for row in rows if row["status"] == "FAILED"]
    result = {"docs_consistency_status": "FAILED" if failed else "PASSED", "checks_total": len(rows), "checks_passed": len(rows) - len(failed), "checks_failed": len(failed), "blocking_issues": [row["item"] for row in failed], "safety": _safety()}
    matrix = out / "docs_consistency_matrix.csv"
    report = out / "docs_consistency_report.md"
    json_path = out / "docs_consistency_results.json"
    pd.DataFrame(rows).to_csv(matrix, index=False)
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    report.write_text("# v1.9 Docs Consistency Report\n\n" + _table(pd.DataFrame(rows)) + "\n", encoding="utf-8")
    result.update({"docs_consistency_report_path": str(report.resolve()), "docs_consistency_results_json_path": str(json_path.resolve()), "docs_consistency_matrix_path": str(matrix.resolve())})
    return result


def _table(frame: pd.DataFrame) -> str:
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)


def _safety() -> dict[str, bool]:
    return {"network_calls_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False, "automatic_betting_enabled": False}
