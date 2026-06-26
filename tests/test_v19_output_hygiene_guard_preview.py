# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from football_prediction_v19.analysis.v19_output_hygiene_guard_preview import run_output_hygiene_guard


def test_output_hygiene_passes_clean_warns_generated_and_no_git_crash(tmp_path: Path) -> None:
    clean = run_output_hygiene_guard(tmp_path / "clean", ["src/example.py"])
    warn = run_output_hygiene_guard(tmp_path / "warn", ["outputs/analysis_preview/demo.md"])
    nogit = run_output_hygiene_guard(tmp_path / "nogit", repo_root=tmp_path / "missing")
    assert clean["output_hygiene_status"] == "PASSED"
    assert warn["output_hygiene_status"] == "WARNING"
    assert nogit["output_hygiene_status"] in {"PASSED", "WARNING"}
    assert Path(warn["output_hygiene_file_matrix_path"]).exists()
