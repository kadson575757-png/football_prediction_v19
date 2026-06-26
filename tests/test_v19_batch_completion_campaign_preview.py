# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.run_v19_batch_workbench_preview import run_v19_batch_workbench_preview
from scripts.build_v19_batch_completion_campaign_preview import build_v19_batch_completion_campaign_preview


ROOT = Path(__file__).resolve().parents[1]
BATCH_CONFIG = ROOT / "tests" / "fixtures" / "batch_workbench" / "lazio_atalanta_batch_config.csv"


def test_batch_completion_campaign_builds_master_template_and_reports(tmp_path: Path) -> None:
    workbench = run_v19_batch_workbench_preview(batch_config=BATCH_CONFIG, output_dir=tmp_path / "batch", emit_all=True, base_dir=ROOT)
    result = build_v19_batch_completion_campaign_preview(
        batch_results_json=workbench["batch_results_json_path"],
        output_dir=tmp_path / "campaign",
        emit_all=True,
        base_dir=ROOT,
    )

    assert result["batch_completion_campaign_status"] == "V19_BATCH_COMPLETION_CAMPAIGN_PREVIEW_READY"
    assert result["batch_completion_campaign_enabled"] is True
    assert int(result["fillable_fields_total"]) >= 20
    assert int(result["critical_fields_total"]) >= 20
    assert int(result["matches_with_critical_blockers"]) == 1

    template = pd.read_csv(result["master_completion_template_path"], keep_default_na=False)
    assert {"match_id", "field_group", "field_name", "user_value", "priority"}.issubset(template.columns)
    assert template["user_value"].astype(str).str.strip().eq("").all()
    assert {"Market", "Availability", "Recent Form", "Big Chances"}.issubset(set(template["field_group"]))

    dashboard = Path(result["campaign_dashboard_path"]).read_text(encoding="utf-8")
    assert "v1.9 Batch Completion Campaign Dashboard" in dashboard
    assert "Preview only. No production betting. No stake. No ROI." in dashboard

    summary = json.loads(Path(result["campaign_summary_json_path"]).read_text(encoding="utf-8"))
    assert summary["safety"]["network_calls_enabled"] is False
    assert summary["safety"]["betting_logic_enabled"] is False
    assert summary["safety"]["staking_logic_enabled"] is False
    assert summary["safety"]["roi_logic_enabled"] is False
