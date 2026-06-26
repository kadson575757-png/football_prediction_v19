# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from scripts.run_v19_final_pipeline_preview import run_v19_final_pipeline_preview

ROOT = Path(__file__).resolve().parents[1]


def test_final_pipeline_all_four_input_modes_work(tmp_path: Path) -> None:
    cases = [
        ("RAW_EVIDENCE", {"raw_input_dir": ROOT / "tests/fixtures/raw_evidence_intake"}),
        ("MATCH_PACK_MANIFEST", {"match_pack_manifest": ROOT / "tests/fixtures/match_packs/match_pack_manifest.csv"}),
        ("BATCH_CONFIG", {"batch_config": ROOT / "tests/fixtures/batch_workbench/lazio_atalanta_batch_config.csv"}),
        ("SINGLE_MATCH", {"single_match_input_dir": ROOT / "tests/fixtures/excel_evidence/lazio_atalanta_2026_02_14", "home_team": "Lazio", "away_team": "Atalanta", "competition": "Serie A", "season": "2025/26", "match_date": "2026-02-14"}),
    ]
    for mode, kwargs in cases:
        result = run_v19_final_pipeline_preview(**kwargs, output_dir=tmp_path / mode.lower(), emit_all=True, base_dir=ROOT)
        assert result["input_mode"] == mode
        assert result["v19_final_pipeline_status"] == "V19_FINAL_PIPELINE_PREVIEW_READY"
        assert result["batch_os_status"] == "V19_BATCH_OS_PREVIEW_READY"
        assert Path(result["final_dashboard_path"]).exists()
