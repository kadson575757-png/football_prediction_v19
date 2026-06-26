# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from football_prediction_v19.analysis.v19_cli_command_validation_preview import run_cli_command_validation
ROOT = Path(__file__).resolve().parents[1]


def test_cli_validation_checks_scripts_and_docs(tmp_path: Path) -> None:
    result = run_cli_command_validation(tmp_path, repo_root=ROOT)
    assert result["cli_command_validation_status"] == "PASSED"
    assert Path(result["cli_command_matrix_path"]).exists()
    assert result["safety"]["betting_logic_enabled"] is False
