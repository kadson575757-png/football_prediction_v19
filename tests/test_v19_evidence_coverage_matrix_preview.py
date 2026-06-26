# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.scan_v19_match_packs_preview import scan_v19_match_packs_preview

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "tests" / "fixtures" / "match_packs" / "match_pack_manifest.csv"


def test_evidence_coverage_matrix_contains_all_groups_and_critical_missing(tmp_path: Path) -> None:
    scan = scan_v19_match_packs_preview(manifest=MANIFEST, output_dir=tmp_path / "scan", emit_all=True, base_dir=ROOT)
    matrix_path = Path(scan["evidence_coverage_matrix_path"])
    md_path = Path(scan["evidence_coverage_matrix_md_path"])

    assert matrix_path.exists()
    assert md_path.exists()
    matrix = pd.read_csv(matrix_path, keep_default_na=False)
    for column in [
        "team_xg",
        "player_xg_xa",
        "match_stats",
        "formation_or_tactical",
        "odds_current",
        "recent_form",
        "big_chances",
        "availability",
        "opening_closing_odds",
        "dnb_ou_market",
        "referee_weather",
        "tactical_details",
        "coverage_score",
    ]:
        assert column in matrix.columns

    lazio = matrix[matrix["match_id"].eq("lazio_atalanta_2026_02_14")].iloc[0]
    assert float(lazio["coverage_score"]) > 50
    assert "recent_form" in str(lazio["critical_groups_missing"])
