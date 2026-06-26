# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
import pandas as pd
from football_prediction_v19.analysis.v19_match_pack_auto_assembler_preview import assemble_match_pack_manifest
ROOT = Path(__file__).resolve().parents[1]
def test_match_pack_auto_assembler_creates_manifest(tmp_path: Path) -> None:
    r = assemble_match_pack_manifest(ROOT / "tests/fixtures/raw_evidence_intake", tmp_path)
    assert r["match_pack_auto_assembler_status"] == "V19_MATCH_PACK_AUTO_ASSEMBLER_PREVIEW_READY"
    frame = pd.read_csv(r["auto_match_pack_manifest_path"], keep_default_na=False)
    assert len(frame) >= 3
    assert "synthetic_demo_pack" in frame.columns
