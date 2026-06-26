# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from scripts.run_v19_final_pipeline_preview import run_v19_final_pipeline_preview

ROOT = Path(__file__).resolve().parents[1]


def test_final_dashboard_contains_required_sections(tmp_path: Path) -> None:
    result = run_v19_final_pipeline_preview(batch_config=ROOT / "tests/fixtures/batch_workbench/lazio_atalanta_batch_config.csv", output_dir=tmp_path / "final", emit_all=True, base_dir=ROOT)
    text = Path(result["final_dashboard_path"]).read_text(encoding="utf-8")
    for phrase in ["Final Pipeline Status", "What This Pipeline Can Do", "Release Readiness Summary", "What To Do Next", "Safety Footer"]:
        assert phrase in text
