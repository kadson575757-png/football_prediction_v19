# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.run_v19_match_workbench_preview import run_v19_match_workbench_preview


ROOT = Path(__file__).resolve().parents[1]
EXCEL_FIXTURE = ROOT / "tests" / "fixtures" / "excel_evidence" / "lazio_atalanta_2026_02_14"
COMPLETION_FIXTURE = ROOT / "tests" / "fixtures" / "manual_evidence_completion" / "lazio_atalanta_completion.csv"


def _run(tmp_path: Path) -> dict[str, object]:
    return run_v19_match_workbench_preview(
        input_dir=EXCEL_FIXTURE,
        home_team="Lazio",
        away_team="Atalanta",
        competition="Serie A",
        season="2025/26",
        match_date="2026-02-14",
        manual_evidence_completion=COMPLETION_FIXTURE,
        emit_all=True,
        output_dir=tmp_path / "v19_match_workbench",
        base_dir=ROOT,
    )


def test_v19_match_workbench_creates_output_bundle(tmp_path: Path) -> None:
    result = _run(tmp_path)

    assert result["v19_match_workbench_status"] == "V19_MATCH_WORKBENCH_PREVIEW_READY"
    assert result["workbench_preview_enabled"] is True
    assert int(result["workbench_artifacts_count"]) >= 13
    out = Path(str(result["workbench_output_dir"]))
    for name in [
        "workbench_dashboard.md",
        "workbench_summary.md",
        "real_match_intake.csv",
        "completion_template.csv",
        "completion_validation_report.md",
        "completion_validation.json",
        "production_readiness_report.md",
        "promotion_downgrade_simulation.md",
        "next_data_to_fill.md",
        "final_decision_card.md",
        "analysis_suite_summary.md",
        "machine_readable_workbench.json",
        "workbench_bundle_index.csv",
    ]:
        assert (out / name).exists()

    assert int(result["excel_files_detected"]) == 10
    assert int(result["fields_mapped_count"]) >= 21
    assert result["manual_evidence_completion_status"] == "MANUAL_EVIDENCE_COMPLETION_APPLIED"
    assert int(result["fields_completed_count"]) == 15
    assert int(result["remaining_missing_fields_count"]) == 44
    assert result["v19_analysis_suite_status"] == "V19_ANALYSIS_SUITE_PREVIEW_READY"
    assert result["v19_production_readiness_gate_status"] == "V19_PRODUCTION_READINESS_GATE_PREVIEW_READY"
    assert int(result["evidence_readiness_score"]) == 85
    assert result["final_decision_class"] == "ANALYST_LEAN_ONLY"
    assert result["promotion_allowed"] is False
    assert result["strong_promotion_allowed"] is False
    assert result["conflict_score"] == "HIGH"


def test_v19_match_workbench_reports_are_user_readable(tmp_path: Path) -> None:
    result = _run(tmp_path)
    out = Path(str(result["workbench_output_dir"]))

    dashboard = (out / "workbench_dashboard.md").read_text(encoding="utf-8")
    for phrase in [
        "v1.9 Match Workbench Dashboard",
        "Current Final Status",
        "What We Know",
        "What Blocks Promotion",
        "What To Fill Next",
        "What Could Upgrade",
        "What Could Downgrade",
        "No production bet",
    ]:
        assert phrase in dashboard

    validation = (out / "completion_validation_report.md").read_text(encoding="utf-8")
    for phrase in [
        "Completion Status",
        "fields_completed_count",
        "remaining_missing_fields_count",
        "Recent Form missing",
        "Big Chances missing",
        "Market/Odds partial",
        "Availability partial",
    ]:
        assert phrase in validation

    simulation = (out / "promotion_downgrade_simulation.md").read_text(encoding="utf-8")
    for phrase in [
        "Current State",
        "Add Recent Form only",
        "Add Recent Form + Big Chances",
        "Add Full Availability",
        "Add Opening/Closing Odds",
        "All Critical Blockers Resolved",
        "Downgrade Scenario",
    ]:
        assert phrase in simulation

    next_data = (out / "next_data_to_fill.md").read_text(encoding="utf-8")
    for phrase in [
        "Recent Form",
        "Big Chances",
        "Availability",
        "Market",
        "Minimum Input Set To Rerun",
        "Copy/Paste CSV Fill Guide",
    ]:
        assert phrase in next_data


def test_v19_match_workbench_machine_json_and_safety(tmp_path: Path) -> None:
    result = _run(tmp_path)
    machine = json.loads(Path(str(result["machine_readable_workbench_path"])).read_text(encoding="utf-8"))

    assert machine["workbench_status"] == "V19_MATCH_WORKBENCH_PREVIEW_READY"
    assert machine["match"]["home_team"] == "Lazio"
    assert machine["completion_validation"]
    assert machine["production_readiness"]
    assert machine["promotion_simulation"]
    assert machine["artifact_paths"]
    assert machine["safety"]["network_calls_enabled"] is False
    assert machine["safety"]["betting_logic_enabled"] is False
    assert machine["safety"]["staking_logic_enabled"] is False
    assert machine["safety"]["roi_logic_enabled"] is False
    assert machine["safety"]["workbench_preview_enabled"] is True


def test_v19_match_workbench_cli_outputs_required_fields(tmp_path: Path) -> None:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_v19_match_workbench_preview.py"),
        "--input-dir",
        str(EXCEL_FIXTURE),
        "--home-team",
        "Lazio",
        "--away-team",
        "Atalanta",
        "--competition",
        "Serie A",
        "--season",
        "2025/26",
        "--match-date",
        "2026-02-14",
        "--manual-evidence-completion",
        str(COMPLETION_FIXTURE),
        "--emit-all",
        "--output-dir",
        str(tmp_path / "cli_workbench"),
        "--base-dir",
        str(ROOT),
    ]
    completed = subprocess.run(cmd, check=True, capture_output=True, text=True)
    stdout = completed.stdout
    for phrase in [
        "v19_match_workbench_status=V19_MATCH_WORKBENCH_PREVIEW_READY",
        "workbench_preview_enabled=true",
        "final_decision_class=ANALYST_LEAN_ONLY",
        "promotion_allowed=false",
        "strong_promotion_allowed=false",
        "network_calls_enabled=false",
        "betting_logic_enabled=false",
        "staking_logic_enabled=false",
        "roi_logic_enabled=false",
    ]:
        assert phrase in stdout
    artifacts_line = [line for line in stdout.splitlines() if line.startswith("workbench_artifacts_count=")][0]
    assert int(artifacts_line.split("=", 1)[1]) >= 13
