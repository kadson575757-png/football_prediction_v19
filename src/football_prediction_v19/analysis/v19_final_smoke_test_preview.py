# -*- coding: utf-8 -*-
"""Final v1.9 smoke test harness preview."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

V19_FINAL_SMOKE_TESTS_PASSED = "V19_FINAL_SMOKE_TESTS_PASSED"


def write_final_smoke_test_report(output_dir: str | Path, test_rows: list[dict[str, object]]) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    failed = [row for row in test_rows if row.get("status") != "PASSED"]
    result = {"final_smoke_test_status": V19_FINAL_SMOKE_TESTS_PASSED if not failed else "V19_FINAL_SMOKE_TESTS_FAILED", "tests_total": len(test_rows), "tests_passed": len(test_rows) - len(failed), "tests_failed": len(failed), "failed_tests": [row.get("test_name") for row in failed], "safety": {"network_calls_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}}
    matrix = out / "final_smoke_test_matrix.csv"
    report = out / "final_smoke_test_report.md"
    json_path = out / "final_smoke_test_report.json"
    bundle = out / "final_smoke_test_bundle_index.csv"
    pd.DataFrame(test_rows).to_csv(matrix, index=False)
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    report.write_text("# v1.9 Final Smoke Test Report\n\n" + _table(pd.DataFrame(test_rows)) + "\n\nNo production betting. No stake. No ROI.\n", encoding="utf-8")
    pd.DataFrame([{"artifact_name": "final_smoke_test_report", "path": str(report), "status": "READY"}, {"artifact_name": "final_smoke_test_report_json", "path": str(json_path), "status": "READY"}, {"artifact_name": "final_smoke_test_matrix", "path": str(matrix), "status": "READY"}]).to_csv(bundle, index=False)
    result.update({"final_smoke_test_report_path": str(report.resolve()), "final_smoke_test_report_json_path": str(json_path.resolve()), "final_smoke_test_matrix_path": str(matrix.resolve()), "final_smoke_test_bundle_index_path": str(bundle.resolve()), "network_calls_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False})
    return result


def _table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "No rows."
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)
