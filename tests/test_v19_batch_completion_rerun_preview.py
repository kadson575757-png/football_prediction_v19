# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.build_v19_batch_completion_campaign_preview import build_v19_batch_completion_campaign_preview
from scripts.run_v19_batch_completion_rerun_preview import run_v19_batch_completion_rerun_preview
from scripts.run_v19_batch_workbench_preview import run_v19_batch_workbench_preview


ROOT = Path(__file__).resolve().parents[1]
BATCH_CONFIG = ROOT / "tests" / "fixtures" / "batch_workbench" / "lazio_atalanta_batch_config.csv"


def _build_campaign(tmp_path: Path) -> tuple[dict[str, object], dict[str, object]]:
    workbench = run_v19_batch_workbench_preview(batch_config=BATCH_CONFIG, output_dir=tmp_path / "batch", emit_all=True, base_dir=ROOT)
    campaign = build_v19_batch_completion_campaign_preview(
        batch_results_json=workbench["batch_results_json_path"],
        output_dir=tmp_path / "campaign",
        emit_all=True,
        base_dir=ROOT,
    )
    return workbench, campaign


def test_empty_batch_completion_rerun_keeps_portfolio_unchanged(tmp_path: Path) -> None:
    workbench, campaign = _build_campaign(tmp_path)
    result = run_v19_batch_completion_rerun_preview(
        base_batch_results_json=workbench["batch_results_json_path"],
        filled_master_completion_csv=campaign["master_completion_template_path"],
        batch_config=BATCH_CONFIG,
        output_dir=tmp_path / "rerun",
        emit_all=True,
        base_dir=ROOT,
    )

    assert result["batch_completion_rerun_status"] == "V19_BATCH_COMPLETION_RERUN_PREVIEW_READY"
    assert result["portfolio_delta_status"] == "V19_PORTFOLIO_DELTA_PREVIEW_READY"
    assert int(result["filled_values_count"]) == 0
    assert int(result["candidate_count_delta"]) == 0
    assert float(result["average_readiness_delta"]) == 0
    assert Path(result["portfolio_delta_dashboard_path"]).exists()
    assert Path(result["candidate_change_report_path"]).exists()
    assert Path(result["no_bet_change_report_path"]).exists()
    assert Path(result["missing_data_progress_report_path"]).exists()

    delta = json.loads(Path(result["portfolio_delta_json_path"]).read_text(encoding="utf-8"))
    assert delta["final_summary"] == "No filled values; portfolio unchanged."
    assert delta["network_calls_enabled"] is False
    assert delta["betting_logic_enabled"] is False
    assert delta["staking_logic_enabled"] is False
    assert delta["roi_logic_enabled"] is False


def test_filled_batch_completion_rerun_can_unlock_preview_candidate(tmp_path: Path) -> None:
    workbench, campaign = _build_campaign(tmp_path)
    template_path = Path(campaign["master_completion_template_path"])
    frame = pd.read_csv(template_path, keep_default_na=False)
    for group in ["Recent Form", "Big Chances", "Availability", "Market"]:
        index = frame.index[frame["field_group"].eq(group)][0]
        frame.loc[index, "user_value"] = "filled preview value"
    filled = tmp_path / "filled_master_completion_template.csv"
    frame.to_csv(filled, index=False)

    result = run_v19_batch_completion_rerun_preview(
        base_batch_results_json=workbench["batch_results_json_path"],
        filled_master_completion_csv=filled,
        batch_config=BATCH_CONFIG,
        output_dir=tmp_path / "rerun_filled",
        emit_all=True,
        base_dir=ROOT,
    )

    assert int(result["filled_values_count"]) == 4
    assert int(result["candidate_count_delta"]) == 1
    assert int(result["matches_upgraded_count"]) == 1
    rerun_payload = json.loads(Path(result["batch_rerun_results_json_path"]).read_text(encoding="utf-8"))
    assert rerun_payload["matches"][0]["final_decision_class"] == "BET_CANDIDATE_PREVIEW"
