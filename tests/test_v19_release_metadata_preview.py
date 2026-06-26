# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from pathlib import Path
from football_prediction_v19.analysis.v19_release_metadata_preview import write_release_metadata


def test_release_metadata_contains_release_name_modes_and_entrypoints(tmp_path: Path) -> None:
    result = write_release_metadata(tmp_path)
    payload = json.loads(Path(result["release_metadata_json_path"]).read_text(encoding="utf-8"))
    assert payload["release_name"] == "v1.9 Final Release Candidate Preview"
    assert "raw evidence" in payload["supported_modes"]
    assert payload["main_entrypoint"] == "scripts/run_v19_final_pipeline_preview.py"
    assert Path(result["release_metadata_md_path"]).exists()
