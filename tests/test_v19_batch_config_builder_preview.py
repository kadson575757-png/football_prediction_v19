# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.build_v19_batch_config_from_match_packs_preview import build_v19_batch_config_from_match_packs_preview

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "match_packs" / "match_pack_manifest.csv"


def test_batch_config_builder_includes_runnable_packs_and_excludes_blocked(tmp_path: Path) -> None:
    result = build_v19_batch_config_from_match_packs_preview(manifest=MANIFEST, output=tmp_path / "auto_batch_config.csv", emit_all=True, base_dir=ROOT)

    assert result["batch_config_builder_status"] == "V19_BATCH_CONFIG_BUILDER_PREVIEW_READY"
    assert int(result["matches_included"]) >= 1
    assert int(result["matches_excluded"]) >= 1
    assert Path(result["output_path"]).exists()
    assert Path(result["report_path"]).exists()

    frame = pd.read_csv(result["output_path"], keep_default_na=False)
    assert list(frame.columns) == ["match_id", "input_dir", "home_team", "away_team", "competition", "season", "match_date", "manual_evidence_completion", "run_transition_lab", "notes"]
    assert "lazio_atalanta_2026_02_14" in set(frame["match_id"])
    assert "demo_match_pack_missing_market_01" not in set(frame["match_id"])
    report = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "Excluded Matches" in report
    assert "No production betting" in report
