# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.run_v19_batch_os_preview import run_v19_batch_os_preview


ROOT = Path(__file__).resolve().parents[1]
BATCH_CONFIG = ROOT / "tests" / "fixtures" / "batch_workbench" / "lazio_atalanta_batch_config.csv"


def test_batch_os_one_command_preview_writes_all_core_artifacts(tmp_path: Path) -> None:
    result = run_v19_batch_os_preview(batch_config=BATCH_CONFIG, output_dir=tmp_path / "batch_os", emit_all=True, base_dir=ROOT)

    assert result["batch_os_status"] == "V19_BATCH_OS_PREVIEW_READY"
    assert result["batch_os_preview_enabled"] is True
    assert result["batch_workbench_status"] == "V19_BATCH_WORKBENCH_PREVIEW_READY"
    assert result["batch_completion_campaign_status"] == "V19_BATCH_COMPLETION_CAMPAIGN_PREVIEW_READY"
    assert result["batch_completion_rerun_status"] == "V19_BATCH_COMPLETION_RERUN_PREVIEW_READY"
    assert result["portfolio_delta_status"] == "V19_PORTFOLIO_DELTA_PREVIEW_READY"
    assert result["scenario_batch_lab_status"] == "V19_SCENARIO_BATCH_LAB_PREVIEW_READY"
    assert int(result["matches_total"]) == 1
    assert int(result["matches_succeeded"]) == 1
    assert int(result["matches_failed"]) == 0
    assert int(result["fillable_fields_total"]) >= 20
    assert int(result["critical_fields_total"]) >= 20
    assert int(result["filled_values_count"]) == 0
    assert int(result["candidate_count_delta"]) == 0
    assert float(result["average_readiness_delta"]) == 0

    for flag in [
        "batch_workbench_enabled",
        "batch_completion_campaign_enabled",
        "batch_completion_rerun_enabled",
        "portfolio_delta_enabled",
        "scenario_batch_lab_enabled",
        "executive_dashboard_enabled",
    ]:
        assert result[flag] is True

    for flag in [
        "network_calls_enabled",
        "prediction_logic_enabled",
        "betting_logic_enabled",
        "staking_logic_enabled",
        "roi_logic_enabled",
    ]:
        assert result[flag] is False

    for key in [
        "executive_dashboard_path",
        "batch_os_summary_path",
        "batch_dashboard_path",
        "campaign_dashboard_path",
        "master_completion_template_path",
        "portfolio_delta_dashboard_path",
        "candidate_change_report_path",
        "no_bet_change_report_path",
        "missing_data_progress_report_path",
        "readiness_delta_ranking_path",
        "scenario_batch_lab_dashboard_path",
        "final_action_plan_path",
        "batch_os_results_json_path",
        "batch_os_bundle_index_path",
    ]:
        assert Path(result[key]).exists(), key

    dashboard = Path(result["executive_dashboard_path"]).read_text(encoding="utf-8")
    assert "v1.9 Batch Operating System Executive Dashboard" in dashboard
    assert "No production betting. No stake. No ROI. No automatic betting." in dashboard

    payload = json.loads(Path(result["batch_os_results_json_path"]).read_text(encoding="utf-8"))
    assert payload["batch_os_status"] == "V19_BATCH_OS_PREVIEW_READY"
    assert payload["safety"]["network_calls_enabled"] is False
    assert payload["safety"]["prediction_logic_enabled"] is False
    assert payload["safety"]["betting_logic_enabled"] is False
    assert payload["safety"]["staking_logic_enabled"] is False
    assert payload["safety"]["roi_logic_enabled"] is False
    assert payload["safety"]["batch_os_preview_enabled"] is True

    bundle = pd.read_csv(result["batch_os_bundle_index_path"], keep_default_na=False)
    assert set(bundle["status"]) == {"READY"}
    assert {"executive_dashboard", "batch_os_results", "bundle"}.issubset(set(bundle["artifact_name"]))
