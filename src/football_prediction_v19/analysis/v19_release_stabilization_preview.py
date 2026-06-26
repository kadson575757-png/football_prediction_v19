# -*- coding: utf-8 -*-
"""v1.9 release stabilization runner."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v19_cli_command_validation_preview import run_cli_command_validation
from football_prediction_v19.analysis.v19_docs_consistency_check_preview import run_docs_consistency_check
from football_prediction_v19.analysis.v19_final_acceptance_gate_preview import run_final_acceptance_gate
from football_prediction_v19.analysis.v19_output_hygiene_guard_preview import run_output_hygiene_guard
from football_prediction_v19.analysis.v19_release_checklist_preview import write_release_checklist
from football_prediction_v19.analysis.v19_release_metadata_preview import write_release_metadata
from football_prediction_v19.analysis.v19_release_notes_preview import write_release_notes
from football_prediction_v19.analysis.v19_release_stabilization_dashboard_preview import write_release_stabilization_dashboard
from football_prediction_v19.analysis.v19_safety_invariant_scan_preview import run_safety_invariant_scan
from scripts.run_v19_final_smoke_tests_preview import run_v19_final_smoke_tests_preview


def run_release_stabilization(output_dir: str | Path, *, emit_all: bool = False, repo_root: str | Path = ".") -> dict[str, object]:
    root = Path(repo_root).resolve()
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    smoke = run_v19_final_smoke_tests_preview(out / "smoke_tests", emit_all=True, base_dir=root)
    safety_paths = [smoke.get("final_smoke_test_report_json_path", "")]
    safety = run_safety_invariant_scan(out, safety_paths)
    hygiene = run_output_hygiene_guard(out, repo_root=root)
    cli = run_cli_command_validation(out, repo_root=root)
    docs = run_docs_consistency_check(out, repo_root=root)
    acceptance = run_final_acceptance_gate(out, safety, hygiene, cli, docs, smoke)
    checklist = write_release_checklist(out)
    notes = write_release_notes(out)
    metadata = write_release_metadata(out)
    rows = [
        {"check": "Safety Invariant Scan", "status": safety["safety_invariant_status"], "blocking_issues": safety.get("blocking_issues", []), "warnings": [], "next_action": "none"},
        {"check": "Output Hygiene Guard", "status": hygiene["output_hygiene_status"], "blocking_issues": hygiene.get("blocking_issues", []), "warnings": hygiene.get("warnings", []), "next_action": "review warnings" if hygiene.get("warnings") else "none"},
        {"check": "CLI Command Validation", "status": cli["cli_command_validation_status"], "blocking_issues": cli.get("blocking_issues", []), "warnings": [], "next_action": "none"},
        {"check": "Docs Consistency Check", "status": docs["docs_consistency_status"], "blocking_issues": docs.get("blocking_issues", []), "warnings": [], "next_action": "none"},
        {"check": "Final Acceptance Gate", "status": acceptance["final_acceptance_status"], "blocking_issues": acceptance.get("blocking_issues", []), "warnings": acceptance.get("warnings", []), "next_action": acceptance.get("recommendation", "")},
    ]
    dashboard = write_release_stabilization_dashboard(out / "release_stabilization_dashboard.md", rows, acceptance)
    bundle = out / "release_stabilization_bundle_index.csv"
    artifacts = {
        "release_stabilization_dashboard": dashboard,
        "final_acceptance_report": acceptance["final_acceptance_report_path"],
        "safety_invariant_report": safety["safety_invariant_report_path"],
        "output_hygiene_report": hygiene["output_hygiene_report_path"],
        "cli_command_validation_report": cli["cli_command_validation_report_path"],
        "docs_consistency_report": docs["docs_consistency_report_path"],
        "release_checklist": checklist["release_checklist_path"],
        "release_notes": notes["release_notes_path"],
        "release_metadata": metadata["release_metadata_json_path"],
    }
    pd.DataFrame([{"artifact_name": k, "path": v, "status": "READY" if Path(v).exists() else "MISSING"} for k, v in artifacts.items()]).to_csv(bundle, index=False)
    result = {"v19_release_stabilization_status": "V19_RELEASE_STABILIZATION_READY", "final_acceptance_status": acceptance["final_acceptance_status"], "safety_invariant_status": safety["safety_invariant_status"], "output_hygiene_status": hygiene["output_hygiene_status"], "cli_command_validation_status": cli["cli_command_validation_status"], "docs_consistency_status": docs["docs_consistency_status"], "release_stabilization_dashboard_path": dashboard, "release_stabilization_results_json_path": str((out / "release_stabilization_results.json").resolve()), "release_stabilization_bundle_index_path": str(bundle.resolve()), "network_calls_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False, "automatic_betting_enabled": False, "recommendation": acceptance["recommendation"]}
    (out / "release_stabilization_results.json").write_text(json.dumps({**result, "safety": {"network_calls_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False, "automatic_betting_enabled": False}}, indent=2), encoding="utf-8")
    return result
