# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.build_v19_completion_pack_preview import build_v19_completion_pack_preview
from scripts.run_v19_match_workbench_preview import run_v19_match_workbench_preview


ROOT = Path(__file__).resolve().parents[1]
EXCEL_FIXTURE = ROOT / "tests" / "fixtures" / "excel_evidence" / "lazio_atalanta_2026_02_14"
COMPLETION_FIXTURE = ROOT / "tests" / "fixtures" / "manual_evidence_completion" / "lazio_atalanta_completion.csv"


def _workbench_json(tmp_path: Path) -> Path:
    result = run_v19_match_workbench_preview(
        input_dir=EXCEL_FIXTURE,
        home_team="Lazio",
        away_team="Atalanta",
        competition="Serie A",
        season="2025/26",
        match_date="2026-02-14",
        manual_evidence_completion=COMPLETION_FIXTURE,
        emit_all=True,
        output_dir=tmp_path / "workbench",
        base_dir=ROOT,
    )
    return Path(str(result["machine_readable_workbench_path"]))


def test_completion_pack_generator_creates_expected_files(tmp_path: Path) -> None:
    result = build_v19_completion_pack_preview(
        workbench_json=_workbench_json(tmp_path),
        output_dir=tmp_path / "completion_pack",
        emit_all=True,
        base_dir=ROOT,
    )

    assert result["completion_pack_status"] == "V19_COMPLETION_PACK_PREVIEW_READY"
    assert result["completion_pack_enabled"] is True
    out = Path(str(result["completion_pack_output_dir"]))
    for name in [
        "completion_pack_dashboard.md",
        "completion_fill_template.csv",
        "completion_fill_template.md",
        "critical_fields_only.csv",
        "market_fields_only.csv",
        "availability_fields_only.csv",
        "form_big_chance_fields_only.csv",
        "tactical_fields_only.csv",
        "completion_fill_guide.md",
        "completion_pack.json",
        "completion_pack_bundle_index.csv",
    ]:
        assert (out / name).exists()

    template = pd.read_csv(out / "completion_fill_template.csv", keep_default_na=False)
    assert "user_value" in template.columns
    assert int(result["completion_fields_count"]) >= 20
    assert int(result["critical_fields_count"]) >= 20

    critical = pd.read_csv(out / "critical_fields_only.csv", keep_default_na=False)
    for group in ["Recent Form", "Big Chances", "Availability", "Market"]:
        assert group in set(critical["field_group"])
    for field in ["home_recent_xg_for", "away_big_chances_for", "home_goalkeeper_status", "away_closing_odds"]:
        assert field in set(critical["field_name"])


def test_completion_pack_dashboard_and_json_safety(tmp_path: Path) -> None:
    result = build_v19_completion_pack_preview(
        workbench_json=_workbench_json(tmp_path),
        output_dir=tmp_path / "completion_pack",
        emit_all=True,
        base_dir=ROOT,
    )
    out = Path(str(result["completion_pack_output_dir"]))
    dashboard = (out / "completion_pack_dashboard.md").read_text(encoding="utf-8")
    for phrase in [
        "v1.9 Completion Pack Dashboard",
        "Critical Fields To Fill First",
        "Minimum Useful Fill Set",
        "Market-Specific Fill Sets",
        "How To Use",
        "No automatic betting",
    ]:
        assert phrase in dashboard

    pack = json.loads((out / "completion_pack.json").read_text(encoding="utf-8"))
    assert pack["safety"]["network_calls_enabled"] is False
    assert pack["safety"]["betting_logic_enabled"] is False
    assert pack["safety"]["staking_logic_enabled"] is False
    assert pack["safety"]["roi_logic_enabled"] is False
