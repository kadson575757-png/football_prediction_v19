# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.build_v19_completion_pack_preview import build_v19_completion_pack_preview
from scripts.run_v19_completion_rerun_preview import run_v19_completion_rerun_preview
from scripts.run_v19_match_workbench_preview import run_v19_match_workbench_preview


ROOT = Path(__file__).resolve().parents[1]
EXCEL_FIXTURE = ROOT / "tests" / "fixtures" / "excel_evidence" / "lazio_atalanta_2026_02_14"
COMPLETION_FIXTURE = ROOT / "tests" / "fixtures" / "manual_evidence_completion" / "lazio_atalanta_completion.csv"


def _base_and_pack(tmp_path: Path) -> tuple[Path, Path]:
    workbench = run_v19_match_workbench_preview(
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
    pack = build_v19_completion_pack_preview(
        workbench_json=workbench["machine_readable_workbench_path"],
        output_dir=tmp_path / "completion_pack",
        emit_all=True,
        base_dir=ROOT,
    )
    return Path(str(workbench["machine_readable_workbench_path"])), Path(str(pack["completion_fill_template_path"]))


def test_completion_rerun_empty_values_keeps_decision_unchanged(tmp_path: Path) -> None:
    base_json, template = _base_and_pack(tmp_path)
    result = run_v19_completion_rerun_preview(
        base_workbench_json=base_json,
        filled_completion_csv=template,
        input_dir=EXCEL_FIXTURE,
        home_team="Lazio",
        away_team="Atalanta",
        competition="Serie A",
        season="2025/26",
        match_date="2026-02-14",
        output_dir=tmp_path / "rerun",
        emit_all=True,
        base_dir=ROOT,
    )

    assert result["completion_rerun_status"] == "V19_COMPLETION_RERUN_PREVIEW_READY"
    assert result["decision_delta_status"] == "V19_DECISION_DELTA_PREVIEW_READY"
    assert result["decision_class_changed"] is False
    assert int(result["evidence_readiness_delta"]) == 0
    assert result["promotion_changed"] is False
    assert result["final_decision_class"] == "ANALYST_LEAN_ONLY"
    assert result["promotion_allowed"] is False

    for key in [
        "applied_completion_path",
        "decision_delta_report_path",
        "decision_delta_json_path",
        "blocker_delta_path",
        "market_family_delta_path",
        "readiness_delta_path",
    ]:
        assert Path(str(result[key])).exists()

    delta = json.loads(Path(str(result["decision_delta_json_path"])).read_text(encoding="utf-8"))
    assert delta["delta"]["decision_class_changed"] is False
    assert delta["delta"]["evidence_readiness_delta"] == 0
    assert delta["delta"]["promotion_changed"] is False
    assert delta["safety"]["staking_logic_enabled"] is False
    assert delta["safety"]["roi_logic_enabled"] is False


def test_completion_rerun_reports_no_filled_values_message(tmp_path: Path) -> None:
    base_json, template = _base_and_pack(tmp_path)
    result = run_v19_completion_rerun_preview(
        base_workbench_json=base_json,
        filled_completion_csv=template,
        input_dir=EXCEL_FIXTURE,
        home_team="Lazio",
        away_team="Atalanta",
        competition="Serie A",
        season="2025/26",
        match_date="2026-02-14",
        output_dir=tmp_path / "rerun",
        emit_all=True,
        base_dir=ROOT,
    )
    report = Path(str(result["decision_delta_report_path"])).read_text(encoding="utf-8")
    assert "No decision change because no filled completion values were provided." in report
    blocker = Path(str(result["blocker_delta_path"])).read_text(encoding="utf-8")
    assert "removed blockers: none" in blocker
    assert "promotion_allowed remains false" in blocker


def test_completion_rerun_applies_non_empty_user_values(tmp_path: Path) -> None:
    base_json, template = _base_and_pack(tmp_path)
    frame = pd.read_csv(template, keep_default_na=False)
    frame.loc[frame["field_name"].eq("home_recent_xg_for"), "user_value"] = "1.25"
    frame.loc[frame["field_name"].eq("away_recent_xg_for"), "user_value"] = "1.85"
    filled_path = tmp_path / "filled_completion.csv"
    frame.to_csv(filled_path, index=False)

    result = run_v19_completion_rerun_preview(
        base_workbench_json=base_json,
        filled_completion_csv=filled_path,
        input_dir=EXCEL_FIXTURE,
        home_team="Lazio",
        away_team="Atalanta",
        competition="Serie A",
        season="2025/26",
        match_date="2026-02-14",
        output_dir=tmp_path / "rerun",
        emit_all=True,
        base_dir=ROOT,
    )

    assert int(result["filled_values_count"]) == 2
    applied = pd.read_csv(result["applied_completion_path"], keep_default_na=False)
    assert str(applied.loc[0, "home_recent_xg_for"]) == "1.25"
    assert str(applied.loc[0, "away_recent_xg_for"]) == "1.85"
