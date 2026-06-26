# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from football_prediction_v19.analysis.v19_final_user_guide_preview import write_final_user_guide


def test_final_user_guide_contains_modes_safety_and_completion_instructions(tmp_path: Path) -> None:
    path = Path(write_final_user_guide(tmp_path / "final_user_guide.md"))
    text = path.read_text(encoding="utf-8")
    for phrase in ["What v1.9 Does Not Do", "one match Excel folder", "raw evidence folders", "prepared match packs", "batch config", "fill `user_value` only", "Safety Reminder"]:
        assert phrase in text
