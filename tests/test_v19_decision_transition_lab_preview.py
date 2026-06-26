# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.run_v19_decision_transition_lab_preview import run_v19_decision_transition_lab_preview
from scripts.run_v19_match_workbench_preview import run_v19_match_workbench_preview


ROOT = Path(__file__).resolve().parents[1]
EXCEL_FIXTURE = ROOT / "tests" / "fixtures" / "excel_evidence" / "lazio_atalanta_2026_02_14"
COMPLETION_FIXTURE = ROOT / "tests" / "fixtures" / "manual_evidence_completion" / "lazio_atalanta_completion.csv"


def _base_json(tmp_path: Path) -> Path:
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


def test_decision_transition_lab_runs_all_scenarios(tmp_path: Path) -> None:
    result = run_v19_decision_transition_lab_preview(
        base_workbench_json=_base_json(tmp_path),
        input_dir=EXCEL_FIXTURE,
        home_team="Lazio",
        away_team="Atalanta",
        competition="Serie A",
        season="2025/26",
        match_date="2026-02-14",
        output_dir=tmp_path / "transition_lab",
        emit_all=True,
        base_dir=ROOT,
    )

    assert result["decision_transition_lab_status"] == "V19_DECISION_TRANSITION_LAB_PREVIEW_READY"
    assert result["decision_transition_lab_enabled"] is True
    assert result["test_scenario_mode"] is True
    assert result["synthetic_completion_values"] is True
    assert int(result["scenarios_total"]) == 7
    assert int(result["scenarios_passed"]) >= 5
    for key in [
        "transition_lab_dashboard_path",
        "transition_lab_summary_path",
        "transition_matrix_path",
        "transition_matrix_md_path",
        "scenario_results_json_path",
        "scenario_results_csv_path",
    ]:
        assert Path(str(result[key])).exists()


def test_decision_transition_lab_expected_transitions_and_safety(tmp_path: Path) -> None:
    result = run_v19_decision_transition_lab_preview(
        base_workbench_json=_base_json(tmp_path),
        input_dir=EXCEL_FIXTURE,
        home_team="Lazio",
        away_team="Atalanta",
        competition="Serie A",
        season="2025/26",
        match_date="2026-02-14",
        output_dir=tmp_path / "transition_lab",
        emit_all=True,
        base_dir=ROOT,
    )
    payload = json.loads(Path(str(result["scenario_results_json_path"])).read_text(encoding="utf-8"))
    scenarios = {item["scenario_id"]: item for item in payload["scenarios"]}
    assert scenarios["EMPTY_COMPLETION_CONTROL"]["actual"]["final_decision_class"] == "ANALYST_LEAN_ONLY"
    assert scenarios["POSITIVE_ALIGNMENT_CANDIDATE"]["actual"]["final_decision_class"] == "BET_CANDIDATE_PREVIEW"
    assert scenarios["STRONG_ALIGNMENT_LOW_CONFLICT"]["actual"]["final_decision_class"] == "STRONG_BET_CANDIDATE_PREVIEW"
    assert scenarios["NEGATIVE_ALIGNMENT_NO_BET"]["actual"]["final_decision_class"] == "NO_BET_RECOMMENDED"
    assert scenarios["MIXED_ALIGNMENT_CONFLICT_REVIEW"]["actual"]["final_decision_class"] == "CONFLICT_REVIEW"
    assert scenarios["MARKET_DRIFT_DOWNGRADE"]["actual"]["promotion_allowed"] is False
    assert scenarios["AVAILABILITY_DOWNGRADE"]["actual"]["promotion_allowed"] is False
    assert payload["test_scenario_mode"] is True
    assert payload["safety"]["network_calls_enabled"] is False
    assert payload["safety"]["betting_logic_enabled"] is False
    assert payload["safety"]["staking_logic_enabled"] is False
    assert payload["safety"]["roi_logic_enabled"] is False

    matrix = pd.read_csv(result["transition_matrix_path"], keep_default_na=False)
    for transition_type in ["NO_CHANGE", "PROMOTION", "STRONG_PROMOTION", "DOWNGRADE", "CONFLICT"]:
        assert transition_type in set(matrix["transition_type"])

    dashboard = Path(str(result["transition_lab_dashboard_path"])).read_text(encoding="utf-8")
    assert "v1.9 Decision Transition Lab Preview" in dashboard
    assert "Safety flags remain disabled" in dashboard
