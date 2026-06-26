# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
import pandas as pd
from scripts.run_v19_final_pipeline_preview import run_v19_final_pipeline_preview

ROOT = Path(__file__).resolve().parents[1]


def test_final_artifact_index_contains_open_first_artifacts(tmp_path: Path) -> None:
    result = run_v19_final_pipeline_preview(batch_config=ROOT / "tests/fixtures/batch_workbench/lazio_atalanta_batch_config.csv", output_dir=tmp_path / "final", emit_all=True, base_dir=ROOT)
    csv_path = tmp_path / "final" / "final_artifact_index.csv"
    md_path = tmp_path / "final" / "final_artifact_index.md"
    assert csv_path.exists()
    assert md_path.exists()
    frame = pd.read_csv(csv_path, keep_default_na=False)
    assert "final_pipeline_dashboard" in set(frame["artifact_name"])
    assert "master_completion_template" in set(frame["artifact_name"])
    assert frame["open_first"].astype(str).str.lower().eq("true").any()
    assert Path(result["final_pipeline_bundle_index_path"]).exists()
