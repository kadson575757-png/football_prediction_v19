# -*- coding: utf-8 -*-
"""Final acceptance gate for v1.9 release stabilization."""
from __future__ import annotations

import json
from pathlib import Path


def run_final_acceptance_gate(output_dir: str | Path, safety: dict[str, object], hygiene: dict[str, object], cli: dict[str, object], docs: dict[str, object], smoke: dict[str, object] | None = None) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    blocking = []
    warnings = []
    if safety.get("safety_invariant_status") != "PASSED":
        blocking.append("safety invariant failed")
    if cli.get("cli_command_validation_status") != "PASSED":
        blocking.append("cli command validation failed")
    if docs.get("docs_consistency_status") != "PASSED":
        blocking.append("docs consistency failed")
    if hygiene.get("output_hygiene_status") == "FAILED":
        blocking.append("output hygiene failed")
    elif hygiene.get("output_hygiene_status") == "WARNING":
        warnings.extend(hygiene.get("warnings", []))
    if smoke and smoke.get("final_smoke_test_status") != "V19_FINAL_SMOKE_TESTS_PASSED":
        blocking.append("smoke tests failed")
    elif smoke is None:
        warnings.append("optional smoke report missing")
    status = "V19_FINAL_ACCEPTANCE_BLOCKED" if blocking else ("V19_FINAL_ACCEPTANCE_WARNING" if warnings else "V19_FINAL_ACCEPTANCE_PASSED")
    result = {"final_acceptance_status": status, "checks_total": 5, "checks_passed": 5 - len(blocking), "checks_failed": len(blocking), "blocking_issues": blocking, "warnings": warnings, "recommendation": "V19_READY_TO_TAG_PREVIEW" if not blocking else "FIX_BLOCKING_RELEASE_ISSUES", "safety": _safety()}
    json_path = out / "final_acceptance_result.json"
    report = out / "final_acceptance_report.md"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    report.write_text("# v1.9 Final Acceptance Report\n\n" + "\n".join(f"- {k}: {v}" for k, v in result.items() if k != "safety") + "\n", encoding="utf-8")
    result.update({"final_acceptance_result_json_path": str(json_path.resolve()), "final_acceptance_report_path": str(report.resolve())})
    return result


def _safety() -> dict[str, bool]:
    return {"network_calls_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False, "automatic_betting_enabled": False}
