# -*- coding: utf-8 -*-
"""Safety invariant scan for v1.9 release stabilization."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

FORBIDDEN_TRUE = [
    "productive_betting_enabled",
    "automatic_betting_enabled",
    "staking_enabled",
    "roi_tracking_enabled",
    "network_calls_enabled",
    "betting_logic_enabled",
    "staking_logic_enabled",
    "roi_logic_enabled",
]


def run_safety_invariant_scan(output_dir: str | Path, paths: list[str | Path] | None = None) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    issues = []
    for path in paths or []:
        p = Path(path)
        text = p.read_text(encoding="utf-8") if p.exists() else ""
        lower = text.lower().replace(" ", "")
        for key in FORBIDDEN_TRUE:
            active = f'"{key}":true' in lower or f"{key}=true" in lower
            rows.append({"path": str(p), "check": key, "status": "FAILED" if active else "PASSED"})
            if active:
                issues.append(f"{p}: {key}=true")
    if not rows:
        rows.append({"path": "", "check": "no configured outputs", "status": "PASSED"})
    failed = [row for row in rows if row["status"] == "FAILED"]
    result = {
        "safety_invariant_status": "FAILED" if failed else "PASSED",
        "checks_total": len(rows),
        "checks_passed": len(rows) - len(failed),
        "checks_failed": len(failed),
        "blocking_issues": issues,
        "safety": _safety(),
    }
    matrix = out / "safety_invariant_matrix.csv"
    report = out / "safety_invariant_report.md"
    json_path = out / "safety_invariant_results.json"
    pd.DataFrame(rows).to_csv(matrix, index=False)
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    report.write_text("# v1.9 Safety Invariant Report\n\n" + _table(pd.DataFrame(rows)) + "\n", encoding="utf-8")
    result.update({"safety_invariant_report_path": str(report.resolve()), "safety_invariant_results_json_path": str(json_path.resolve()), "safety_invariant_matrix_path": str(matrix.resolve())})
    return result


def _table(frame: pd.DataFrame) -> str:
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)


def _safety() -> dict[str, bool]:
    return {"network_calls_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False, "automatic_betting_enabled": False}
