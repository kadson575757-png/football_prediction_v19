# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from football_prediction_v19.analysis.v19_release_checklist_preview import write_release_checklist


def test_release_checklist_writes_md_json_and_commands(tmp_path: Path) -> None:
    result = write_release_checklist(tmp_path)
    text = Path(result["release_checklist_path"]).read_text(encoding="utf-8")
    assert "$PY" in text
    assert "Confirm no generated outputs are committed" in text
    assert Path(result["release_checklist_json_path"]).exists()
