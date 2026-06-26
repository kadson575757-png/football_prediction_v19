# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v19_scenario_batch_lab_preview import V19ScenarioBatchLabConfig, V19ScenarioBatchLabRunner
from scripts.run_v19_batch_workbench_preview import run_v19_batch_workbench_preview


ROOT = Path(__file__).resolve().parents[1]
BATCH_CONFIG = ROOT / "tests" / "fixtures" / "batch_workbench" / "lazio_atalanta_batch_config.csv"


def test_scenario_batch_lab_runs_control_candidate_strong_no_bet_and_conflict(tmp_path: Path) -> None:
    workbench = run_v19_batch_workbench_preview(batch_config=BATCH_CONFIG, output_dir=tmp_path / "batch", emit_all=True, base_dir=ROOT)
    result = V19ScenarioBatchLabRunner(
        V19ScenarioBatchLabConfig(
            base_batch_results_json=workbench["batch_results_json_path"],
            output_dir=tmp_path / "scenario_lab",
            emit_all=True,
            base_dir=ROOT,
        )
    ).run()

    assert result.scenario_batch_lab_status == "V19_SCENARIO_BATCH_LAB_PREVIEW_READY"
    assert result.scenarios_total == 5
    assert result.scenarios_passed == 5
    assert result.network_calls_enabled is False
    assert result.betting_logic_enabled is False
    assert result.staking_logic_enabled is False
    assert result.roi_logic_enabled is False

    matrix = pd.read_csv(result.scenario_batch_matrix_path, keep_default_na=False)
    assert set(matrix["scenario_id"]) == {
        "BATCH_EMPTY_CONTROL",
        "BATCH_POSITIVE_CANDIDATE",
        "BATCH_STRONG_CANDIDATE",
        "BATCH_NO_BET",
        "BATCH_CONFLICT",
    }
    assert set(matrix["status"]) == {"PASSED"}

    payload = json.loads(Path(result.scenario_batch_results_json_path).read_text(encoding="utf-8"))
    assert payload["test_scenario_mode"] is True
    assert payload["synthetic_completion_values"] is True
    assert payload["safety"]["network_calls_enabled"] is False
