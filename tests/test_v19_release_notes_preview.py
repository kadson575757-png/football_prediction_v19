# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from football_prediction_v19.analysis.v19_release_notes_preview import write_release_notes


def test_release_notes_include_safety_limitations_and_entrypoints(tmp_path: Path) -> None:
    result = write_release_notes(tmp_path)
    text = Path(result["release_notes_path"]).read_text(encoding="utf-8")
    for phrase in ["Safety Boundaries", "Known Limitations", "Main Entry Points"]:
        assert phrase in text
