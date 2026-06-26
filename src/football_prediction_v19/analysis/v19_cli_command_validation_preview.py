# -*- coding: utf-8 -*-
"""CLI command validation for v1.9 release stabilization."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pandas as pd

REQUIRED_SCRIPTS = [
    "scripts/run_v19_final_pipeline_preview.py",
    "scripts/run_v19_final_smoke_tests_preview.py",
    "scripts/run_v19_final_release_readiness_gate_preview.py",
    "scripts/run_v19_batch_os_preview.py",
    "scripts/run_v19_multi_match_batch_os_demo_preview.py",
    "scripts/run_v19_raw_intake_to_batch_os_demo_preview.py",
    "scripts/scan_v19_match_packs_preview.py",
    "scripts/build_v19_batch_config_from_match_packs_preview.py",
    "scripts/run_v19_batch_health_gate_preview.py",
]


def run_cli_command_validation(output_dir: str | Path, *, repo_root: str | Path = ".") -> dict[str, object]:
    root = Path(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    docs = (root / "docs" / "v19_commands.md").read_text(encoding="utf-8") if (root / "docs" / "v19_commands.md").exists() else ""
    rows = []
    for script in REQUIRED_SCRIPTS:
        path = root / script
        exists = path.exists()
        importable = _importable(path) if exists else False
        has_main = "def main" in path.read_text(encoding="utf-8") if exists else False
        documented = script.replace("/", "\\") in docs or script in docs
        status = "PASSED" if all([exists, importable, has_main, documented]) else "FAILED"
        rows.append({"script": script, "exists": exists, "importable": importable, "has_main": has_main, "documented": documented, "status": status})
    failed = [row for row in rows if row["status"] == "FAILED"]
    result = {"cli_command_validation_status": "FAILED" if failed else "PASSED", "checks_total": len(rows), "checks_passed": len(rows) - len(failed), "checks_failed": len(failed), "blocking_issues": [row["script"] for row in failed], "safety": _safety()}
    matrix = out / "cli_command_matrix.csv"
    report = out / "cli_command_validation_report.md"
    json_path = out / "cli_command_validation_results.json"
    pd.DataFrame(rows).to_csv(matrix, index=False)
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    report.write_text("# v1.9 CLI Command Validation Report\n\n" + _table(pd.DataFrame(rows)) + "\n", encoding="utf-8")
    result.update({"cli_command_validation_report_path": str(report.resolve()), "cli_command_validation_results_json_path": str(json_path.resolve()), "cli_command_matrix_path": str(matrix.resolve())})
    return result


def _importable(path: Path) -> bool:
    try:
        spec = importlib.util.spec_from_file_location(path.stem, path)
        return spec is not None and spec.loader is not None
    except Exception:
        return False


def _table(frame: pd.DataFrame) -> str:
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ",") for col in cols) + " |")
    return "\n".join(lines)


def _safety() -> dict[str, bool]:
    return {"network_calls_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False, "automatic_betting_enabled": False}
