# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

from football_prediction_v19.data_contracts import (
    detect_column_family,
    validate_match_dataframe,
)
from football_prediction_v19.importers.registry import IMPORTER_REGISTRY


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_data_contracts as audit  # noqa: E402


def _valid_df(**extra) -> pd.DataFrame:
    data = {
        "Date": ["01/08/2024", "02/08/2024"],
        "HomeTeam": ["A", "B"],
        "AwayTeam": ["C", "D"],
        "FTHG": [1, 0],
        "FTAG": [0, 2],
        "FTR": ["H", "A"],
    }
    data.update(extra)
    return pd.DataFrame(data)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_required_match_columns_pass_validation():
    result = validate_match_dataframe(_valid_df(B365H=[2.0, 2.1]))

    assert result["missing_required_columns"] == []
    assert result["quality_label"] == "READY_FOR_REPLAY"


def test_missing_required_columns_produce_missing_required_label():
    df = pd.DataFrame({"Date": ["01/08/2024"], "HomeTeam": ["A"]})

    result = validate_match_dataframe(df)

    assert result["quality_label"] == "MISSING_REQUIRED_COLUMNS"
    assert "AwayTeam" in result["missing_required_columns"]


def test_empty_dataframe_produces_empty_data():
    df = pd.DataFrame(columns=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"])

    result = validate_match_dataframe(df)

    assert result["quality_label"] == "EMPTY_DATA"


def test_invalid_score_rows_counted():
    result = validate_match_dataframe(_valid_df(FTHG=[1, -1]))

    assert result["invalid_score_count"] == 1
    assert result["quality_label"] == "INVALID_DATA"


def test_invalid_ftr_rows_counted():
    result = validate_match_dataframe(_valid_df(FTR=["H", "X"]))

    assert result["invalid_result_count"] == 1
    assert result["quality_label"] == "INVALID_DATA"


def test_duplicate_matches_counted():
    df = _valid_df()
    df.loc[1, ["Date", "HomeTeam", "AwayTeam"]] = df.loc[0, ["Date", "HomeTeam", "AwayTeam"]]

    result = validate_match_dataframe(df)

    assert result["duplicate_match_count"] == 1


def test_odds_columns_detected():
    families = detect_column_family(["B365H", "B365D", "B365A"])

    assert families["odds"] == ["B365H", "B365D", "B365A"]


def test_xg_columns_detected():
    families = detect_column_family(["home_xg", "away_xg", "xG_home"])

    assert set(families["xg"]) == {"home_xg", "away_xg", "xG_home"}


def test_context_columns_detected():
    families = detect_column_family(["league", "season", "home_elo", "rest_days_home"])

    assert set(families["context"]) == {"league", "season", "home_elo", "rest_days_home"}


def test_importer_registry_contains_required_placeholder_importers():
    required = {
        "football_data_csv",
        "fixture_csv",
        "api_football_placeholder",
        "understat_placeholder",
        "clubelo_placeholder",
    }

    assert required.issubset(set(IMPORTER_REGISTRY))
    assert IMPORTER_REGISTRY["api_football_placeholder"]["status"] == "PLACEHOLDER"
    assert IMPORTER_REGISTRY["understat_placeholder"]["status"] == "PLACEHOLDER"
    assert IMPORTER_REGISTRY["clubelo_placeholder"]["status"] == "PLACEHOLDER"


def test_audit_script_writes_csv_and_markdown(tmp_path):
    root = tmp_path / "repo"
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    _valid_df(B365H=[2.0, 2.1], B365D=[3.0, 3.1], B365A=[4.0, 4.1]).to_csv(
        raw / "football_data_T1_2024.csv",
        index=False,
    )
    output_dir = root / "outputs" / "diagnostics"

    table, markdown = audit.run(root=root, output_dir=output_dir)

    assert len(table) == 1
    assert (output_dir / audit.OUTPUT_CSV).exists()
    assert (output_dir / audit.OUTPUT_MD).exists()
    assert "Phase 12.1 Data Contract Audit" in markdown
    assert "READY_FOR_IMPORTER_IMPLEMENTATION" in markdown


def test_script_does_not_modify_market_tier_probability_or_recommended_logic(tmp_path):
    protected = [
        ROOT / "src/football_prediction_v19/diagnostics/market_tier.py",
        ROOT / "src/football_prediction_v19/diagnostics/recommended_market.py",
        ROOT / "src/football_prediction_v19/model.py",
    ]
    before = {path: _hash(path) for path in protected}

    root = tmp_path / "repo"
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    _valid_df(B365H=[2.0, 2.1]).to_csv(raw / "football_data_T1_2024.csv", index=False)
    audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    after = {path: _hash(path) for path in protected}
    assert after == before
