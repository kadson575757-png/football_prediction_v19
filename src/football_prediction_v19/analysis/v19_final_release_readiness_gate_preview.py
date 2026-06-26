# -*- coding: utf-8 -*-
"""Final release readiness gate preview."""
from __future__ import annotations

import json
from pathlib import Path

V19_RELEASE_CANDIDATE_READY = "V19_RELEASE_CANDIDATE_READY"
V19_RELEASE_CANDIDATE_PARTIAL = "V19_PARTIAL_RELEASE_CANDIDATE"
V19_RELEASE_CANDIDATE_BLOCKED = "V19_BLOCKED_RELEASE_CANDIDATE"


def run_final_release_readiness_gate(final_pipeline_results_json: str | Path, output_dir: str | Path) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    payload = _read_json(Path(final_pipeline_results_json))
    artifacts = payload.get("artifact_paths", {}) if isinstance(payload.get("artifact_paths", {}), dict) else {}
    checks = [
        ("final runner exists", payload.get("v19_final_pipeline_status") == "V19_FINAL_PIPELINE_PREVIEW_READY"),
        ("batch OS exists", bool(payload.get("batch_os", {}).get("batch_os_status") == "V19_BATCH_OS_PREVIEW_READY") if isinstance(payload.get("batch_os"), dict) else False),
        ("dashboard generated", Path(str(artifacts.get("final_pipeline_dashboard", ""))).exists()),
        ("machine JSON generated", Path(final_pipeline_results_json).exists()),
        ("action plan generated", Path(str(artifacts.get("final_action_plan", ""))).exists()),
        ("artifact index generated", Path(str(artifacts.get("final_artifact_index", ""))).exists()),
        ("user guide generated", Path(str(artifacts.get("final_user_guide", ""))).exists()),
        ("safety network false", payload.get("safety", {}).get("network_calls_enabled") is False),
        ("safety betting false", payload.get("safety", {}).get("betting_logic_enabled") is False),
        ("safety staking false", payload.get("safety", {}).get("staking_logic_enabled") is False),
        ("safety roi false", payload.get("safety", {}).get("roi_logic_enabled") is False),
        ("productive betting disabled", payload.get("safety", {}).get("productive_betting_enabled") is not True),
        ("automatic betting disabled", payload.get("safety", {}).get("automatic_betting_enabled") is not True),
    ]
    failed = [name for name, ok in checks if not ok]
    status = V19_RELEASE_CANDIDATE_READY if not failed else V19_RELEASE_CANDIDATE_BLOCKED
    result = {"final_release_readiness_status": status, "checks_total": len(checks), "checks_passed": len(checks) - len(failed), "checks_failed": len(failed), "blocking_issues": failed, "warnings": [], "recommendation": status, "safety": {"network_calls_enabled": False, "prediction_logic_enabled": False, "betting_logic_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}}
    json_path = out / "final_release_readiness_result.json"
    md_path = out / "final_release_readiness_report.md"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    md_path.write_text("# v1.9 Final Release Readiness Report\n\n" + "\n".join(f"- {k}: {v}" for k, v in result.items() if k != "safety") + "\n\nPreview only. No production betting. No stake. No ROI.\n", encoding="utf-8")
    result["final_release_readiness_result_json_path"] = str(json_path.resolve())
    result["final_release_readiness_report_path"] = str(md_path.resolve())
    return result


def _read_json(path: Path) -> dict[str, object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
