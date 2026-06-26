# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from football_prediction_v19.analysis.v19_safety_invariant_scan_preview import run_safety_invariant_scan


def test_safety_invariant_passes_safe_fixture_and_fails_true_flags(tmp_path: Path) -> None:
    safe = tmp_path / "safe.json"; safe.write_text('{"network_calls_enabled": false, "automatic_betting_enabled": false}', encoding="utf-8")
    bad = tmp_path / "bad.json"; bad.write_text('{"network_calls_enabled": true, "automatic_betting_enabled": true}', encoding="utf-8")
    passed = run_safety_invariant_scan(tmp_path / "pass", [safe])
    failed = run_safety_invariant_scan(tmp_path / "fail", [bad])
    assert passed["safety_invariant_status"] == "PASSED"
    assert failed["safety_invariant_status"] == "FAILED"
    assert failed["safety"]["network_calls_enabled"] is False
    assert Path(passed["safety_invariant_matrix_path"]).exists()
