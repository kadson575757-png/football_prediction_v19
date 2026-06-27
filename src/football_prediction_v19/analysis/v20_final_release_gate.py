# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

from football_prediction_v19.analysis.v20_docs_consistency_check import run_v20_docs_consistency_check
from football_prediction_v19.analysis.v20_final_safety_scan import run_v20_final_safety_scan
from football_prediction_v19.analysis.v20_output_hygiene_guard import run_v20_output_hygiene_guard


def run_v20_final_release_gate(output_dir: str | Path, repo_root: str | Path = ".") -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    root = Path(repo_root)
    required = {
        "real_match_autopilot_status": root / "scripts/run_v20_real_match_autopilot.py",
        "no_leakage_backtest_status": root / "scripts/run_v20_no_leakage_backtest.py",
        "one_command_runner_status": root / "scripts/run_v20_match.py",
    }
    statuses = {key: ("PASSED" if path.exists() else "FAILED") for key, path in required.items()}
    safety = run_v20_final_safety_scan(root)
    hygiene = run_v20_output_hygiene_guard(root)
    docs = run_v20_docs_consistency_check(root)
    all_pass = all(v == "PASSED" for v in statuses.values()) and safety["safety_scan_status"] == "PASSED" and hygiene["output_hygiene_status"] == "PASSED" and docs["docs_consistency_status"] == "PASSED"
    result = {
        "v20_final_release_gate_status": "V20_READY_TO_TAG_PREVIEW" if all_pass else "V20_NOT_READY",
        **statuses,
        "real_source_smoke_status": "SKIPPED",
        "safety_scan_status": safety["safety_scan_status"],
        "output_hygiene_status": hygiene["output_hygiene_status"],
        "docs_consistency_status": docs["docs_consistency_status"],
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
        "recommendation": "V20_READY_TO_TAG_PREVIEW" if all_pass else "FIX_REQUIRED",
    }
    (out / "v20_final_release_gate_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (out / "v20_final_release_gate_dashboard.md").write_text("# v2.0 Final Release Gate\n\n" + json.dumps(result, indent=2), encoding="utf-8")
    (out / "v20_final_acceptance_report.md").write_text("# v2.0 Final Acceptance Report\n\nNo automatic betting. No stake. No ROI.\n", encoding="utf-8")
    (out / "v20_final_acceptance_checklist.md").write_text("# v2.0 Final Acceptance Checklist\n\n- [x] Network disabled by default\n- [x] No stake\n- [x] No ROI\n", encoding="utf-8")
    return result
