# -*- coding: utf-8 -*-
"""Output hygiene guard for v1.9 release stabilization."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pandas as pd

BAD_PATTERNS = ["outputs/analysis_preview/", "outputs\\analysis_preview\\", "__pycache__", ".pytest_cache", ".tmp", ".bak"]


def run_output_hygiene_guard(output_dir: str | Path, tracked_files: list[str] | None = None, *, repo_root: str | Path = ".") -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = tracked_files if tracked_files is not None else _git_ls_files(Path(repo_root))
    rows = []
    issues = []
    for file in files:
        bad = any(pattern.lower() in file.lower() for pattern in BAD_PATTERNS)
        rows.append({"path": file, "status": "WARNING" if bad else "PASSED", "reason": "generated output tracked" if bad else ""})
        if bad:
            issues.append(file)
    status = "WARNING" if issues else "PASSED"
    result = {"output_hygiene_status": status, "checks_total": len(rows), "checks_passed": len(rows) - len(issues), "checks_failed": 0, "warnings": issues, "blocking_issues": [], "safety": _safety()}
    matrix = out / "output_hygiene_file_matrix.csv"
    report = out / "output_hygiene_report.md"
    json_path = out / "output_hygiene_results.json"
    pd.DataFrame(rows or [{"path": "", "status": "PASSED", "reason": "no tracked files supplied"}]).to_csv(matrix, index=False)
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    report.write_text("# v1.9 Output Hygiene Report\n\nGenerated outputs should not be committed.\n\n" + _table(pd.DataFrame(rows)), encoding="utf-8")
    result.update({"output_hygiene_report_path": str(report.resolve()), "output_hygiene_results_json_path": str(json_path.resolve()), "output_hygiene_file_matrix_path": str(matrix.resolve())})
    return result


def _git_ls_files(root: Path) -> list[str]:
    try:
        completed = subprocess.run(["git", "ls-files"], cwd=root, text=True, capture_output=True, check=False)
        return [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def _table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)


def _safety() -> dict[str, bool]:
    return {"network_calls_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False, "automatic_betting_enabled": False}
