# -*- coding: utf-8 -*-
from __future__ import annotations
from football_prediction_v19.analysis.v19_final_acceptance_gate_preview import run_final_acceptance_gate


def test_final_acceptance_passed_blocked_and_warning(tmp_path) -> None:
    safe = {"safety_invariant_status": "PASSED"}
    hygiene = {"output_hygiene_status": "PASSED"}
    cli = {"cli_command_validation_status": "PASSED"}
    docs = {"docs_consistency_status": "PASSED"}
    assert run_final_acceptance_gate(tmp_path / "pass", safe, hygiene, cli, docs, {"final_smoke_test_status": "V19_FINAL_SMOKE_TESTS_PASSED"})["final_acceptance_status"] == "V19_FINAL_ACCEPTANCE_PASSED"
    assert run_final_acceptance_gate(tmp_path / "block", {"safety_invariant_status": "FAILED"}, hygiene, cli, docs)["final_acceptance_status"] == "V19_FINAL_ACCEPTANCE_BLOCKED"
    assert run_final_acceptance_gate(tmp_path / "warn", safe, {"output_hygiene_status": "WARNING", "warnings": ["tracked output"]}, cli, docs, {"final_smoke_test_status": "V19_FINAL_SMOKE_TESTS_PASSED"})["final_acceptance_status"] == "V19_FINAL_ACCEPTANCE_WARNING"
