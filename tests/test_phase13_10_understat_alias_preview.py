from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import apply_understat_team_alias_preview as alias_preview  # noqa: E402


def test_understat_alias_preview_applies_only_accepted_aliases(tmp_path):
    source = tmp_path / "understat.csv"
    alias_map = tmp_path / "aliases.csv"
    pd.DataFrame([
        {"date": "2024-01-01", "home_team": "St Pauli", "away_team": "Kiel", "home_xg": 1.2, "away_xg": 0.8},
    ]).to_csv(source, index=False)
    pd.DataFrame([
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "source_team": "St Pauli", "target_team": "FC St Pauli", "alias_status": "accepted", "notes": ""},
        {"provider": "understat", "league": "Bundesliga", "season": 2024, "source_team": "Kiel", "target_team": "Holstein Kiel", "alias_status": "pending", "notes": ""},
    ]).to_csv(alias_map, index=False)
    out, summary = alias_preview.apply_alias_preview(source, alias_map, tmp_path / "out")
    assert summary["rows_changed"] == 1
    assert out.loc[0, "home_team"] == "FC St Pauli"
    assert out.loc[0, "away_team"] == "Kiel"
