# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

from football_prediction_v19.data_contracts import (
    classify_csv_file,
    summarize_data_quality_by_file_type,
    validate_dataframe_for_file_type,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_data_contracts as audit  # noqa: E402


def _historical(**extra) -> pd.DataFrame:
    data = {
        "Date": ["2024-08-01", "2024-08-02"],
        "HomeTeam": ["A", "B"],
        "AwayTeam": ["C", "D"],
        "FTHG": [1, 0],
        "FTAG": [0, 2],
        "FTR": ["H", "A"],
    }
    data.update(extra)
    return pd.DataFrame(data)


def _fixture() -> pd.DataFrame:
    return pd.DataFrame({
        "date": ["2024-08-01"],
        "home_team": ["A"],
        "away_team": ["B"],
    })


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_template_file_classified_as_template_csv():
    assert classify_csv_file("data/raw/d2_matches_template.csv", ["Date", "HomeTeam"]) == "TEMPLATE_CSV"


def test_upcoming_fixture_file_classified_as_fixture_csv():
    assert classify_csv_file("data/upcoming_fixtures.csv", ["date", "home_team", "away_team"]) == "FIXTURE_CSV"


def test_odds_only_file_classified_as_odds_csv():
    columns = ["Date", "HomeTeam", "AwayTeam", "B365H", "B365D", "B365A"]

    assert classify_csv_file("data/raw/bookmaker_odds.csv", columns) == "ODDS_CSV"


def test_xg_only_file_classified_as_xg_csv():
    columns = ["Date", "HomeTeam", "AwayTeam", "home_xg", "away_xg"]

    assert classify_csv_file("data/raw/league_xg.csv", columns) == "XG_CSV"


def test_full_football_data_style_file_classified_as_historical_match_csv():
    assert classify_csv_file("data/raw/football_data_E0_2024.csv", list(_historical().columns)) == "HISTORICAL_MATCH_CSV"


def test_processed_clean_file_classified_as_processed_feature_csv_when_lacking_scores():
    columns = ["date", "home_team", "away_team", "home_elo"]

    assert classify_csv_file("data/processed/features_clean.csv", columns) == "PROCESSED_FEATURE_CSV"


def test_fixture_file_does_not_require_scores():
    result = validate_dataframe_for_file_type(_fixture(), "FIXTURE_CSV")

    assert result["contract_quality_label"] == "READY_FOR_FIXTURES"
    assert result["missing_contract_columns"] == []


def test_odds_file_requires_valid_odds_triplet():
    missing = pd.DataFrame({"Date": ["2024-08-01"], "HomeTeam": ["A"], "AwayTeam": ["B"], "B365H": [2.0]})
    ok = pd.DataFrame({
        "Date": ["2024-08-01"],
        "HomeTeam": ["A"],
        "AwayTeam": ["B"],
        "B365H": [2.0],
        "B365D": [3.0],
        "B365A": [4.0],
    })

    assert validate_dataframe_for_file_type(missing, "ODDS_CSV")["contract_quality_label"] == "MISSING_REQUIRED_COLUMNS"
    assert validate_dataframe_for_file_type(ok, "ODDS_CSV")["contract_quality_label"] == "READY_FOR_ODDS_ENRICHMENT"


def test_xg_file_requires_valid_xg_pair():
    missing = pd.DataFrame({"Date": ["2024-08-01"], "HomeTeam": ["A"], "AwayTeam": ["B"], "home_xg": [1.2]})
    ok = pd.DataFrame({
        "Date": ["2024-08-01"],
        "HomeTeam": ["A"],
        "AwayTeam": ["B"],
        "home_xg": [1.2],
        "away_xg": [0.9],
    })

    assert validate_dataframe_for_file_type(missing, "XG_CSV")["contract_quality_label"] == "MISSING_REQUIRED_COLUMNS"
    assert validate_dataframe_for_file_type(ok, "XG_CSV")["contract_quality_label"] == "READY_FOR_XG_ENRICHMENT"


def test_template_file_returns_template_only_not_hard_failure():
    result = summarize_data_quality_by_file_type("template.csv", pd.DataFrame({"HomeTeam": ["A"]}))

    assert result["file_type"] == "TEMPLATE_CSV"
    assert result["contract_quality_label"] == "TEMPLATE_ONLY"


def test_audit_output_includes_file_type_and_contract_quality_label(tmp_path):
    root = tmp_path / "repo"
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    _historical(B365H=[2.0, 2.1], B365D=[3.0, 3.1], B365A=[4.0, 4.1]).to_csv(
        raw / "football_data_E0_2024.csv",
        index=False,
    )
    _fixture().to_csv(root / "data" / "upcoming_fixtures.csv", index=False)

    table, markdown = audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    assert "file_type" in table.columns
    assert "contract_quality_label" in table.columns
    assert "Phase 12.2 Data Contract Audit" in markdown
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
    _historical(B365H=[2.0, 2.1], B365D=[3.0, 3.1], B365A=[4.0, 4.1]).to_csv(
        raw / "football_data_E0_2024.csv",
        index=False,
    )
    audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    after = {path: _hash(path) for path in protected}
    assert after == before
