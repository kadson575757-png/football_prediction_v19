# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from scripts.run_v19_final_smoke_tests_preview import run_v19_final_smoke_tests_preview

ROOT = Path(__file__).resolve().parents[1]


def test_final_smoke_harness_passes_and_writes_report(tmp_path: Path) -> None:
    result = run_v19_final_smoke_tests_preview(tmp_path / "smoke", emit_all=True, base_dir=ROOT)
    assert result["final_smoke_test_status"] == "V19_FINAL_SMOKE_TESTS_PASSED"
    assert result["tests_total"] >= 4
    assert result["tests_failed"] == 0
    assert Path(result["final_smoke_test_report_path"]).exists()
    assert result["network_calls_enabled"] is False
    assert result["betting_logic_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
