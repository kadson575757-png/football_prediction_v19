# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

from football_prediction_v19.importers.registry import get_importer
from football_prediction_v19.xg_enrichment import (
    FBREF_XG_EXPORT,
    MATCH_XG_PAIR,
    TEAM_MATCH_XG_LONG,
    UNDERSTAT_XG_EXPORT,
    XG_CONTRACT_EMPTY,
    XG_CONTRACT_MISSING_IDENTITY,
    XG_CONTRACT_MISSING_XG_VALUES,
    detect_xg_schema,
    normalize_xg_column_names,
    validate_xg_dataframe,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_xg_enrichment_contracts as xg_audit  # noqa: E402
import audit_data_contracts as data_audit  # noqa: E402
import plan_data_contract_repairs as repair_plan  # noqa: E402


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_detects_match_xg_pair_home_away_xg():
    df = pd.DataFrame({"Date": ["2024-01-01"], "HomeTeam": ["A"], "AwayTeam": ["B"], "home_xg": [1.2], "away_xg": [0.8]})

    assert detect_xg_schema(list(df.columns)) == MATCH_XG_PAIR


def test_detects_match_xg_pair_xg_home_away():
    df = pd.DataFrame({"Date": ["2024-01-01"], "HomeTeam": ["A"], "AwayTeam": ["B"], "xG_home": [1.2], "xG_away": [0.8]})

    assert detect_xg_schema(list(df.columns)) == MATCH_XG_PAIR


def test_detects_match_xg_pair_hxg_axg():
    df = pd.DataFrame({"date": ["2024-01-01"], "home_team": ["A"], "away_team": ["B"], "hxg": [1.2], "axg": [0.8]})

    assert detect_xg_schema(list(df.columns)) == MATCH_XG_PAIR


def test_detects_team_match_xg_long():
    df = pd.DataFrame({"date": ["2024-01-01"], "team": ["A"], "opponent": ["B"], "xg": [1.1], "xga": [0.9]})

    assert detect_xg_schema(list(df.columns)) == TEAM_MATCH_XG_LONG


def test_detects_fbref_xg_export():
    df = pd.DataFrame({"Date": ["2024-01-01"], "Squad": ["A"], "Opponent": ["B"], "xG": [1.1], "xGA": [0.9]})

    assert detect_xg_schema(list(df.columns)) == FBREF_XG_EXPORT


def test_detects_understat_xg_export():
    df = pd.DataFrame({"date": ["2024-01-01"], "home_team": ["A"], "away_team": ["B"], "home_xG": [1.1], "away_xG": [0.9]})

    assert detect_xg_schema(list(df.columns)) == UNDERSTAT_XG_EXPORT


def test_missing_identity_returns_missing_identity():
    df = pd.DataFrame({"home_xg": [1.0], "away_xg": [0.8]})

    assert validate_xg_dataframe(df)["xg_contract_label"] == XG_CONTRACT_MISSING_IDENTITY


def test_missing_xg_values_returns_missing_xg_values():
    df = pd.DataFrame({"Date": ["2024-01-01"], "HomeTeam": ["A"], "AwayTeam": ["B"], "home_xg": [None], "away_xg": [0.8]})

    assert validate_xg_dataframe(df)["xg_contract_label"] == XG_CONTRACT_MISSING_XG_VALUES


def test_empty_dataframe_returns_empty_contract():
    df = pd.DataFrame(columns=["Date", "HomeTeam", "AwayTeam", "home_xg", "away_xg"])

    assert validate_xg_dataframe(df)["xg_contract_label"] == XG_CONTRACT_EMPTY


def test_negative_xg_rows_are_counted():
    df = pd.DataFrame({"Date": ["2024-01-01"], "HomeTeam": ["A"], "AwayTeam": ["B"], "home_xg": [-0.1], "away_xg": [0.8]})

    assert validate_xg_dataframe(df)["xg_negative_count"] == 1


def test_duplicate_identity_rows_are_counted():
    df = pd.DataFrame({
        "Date": ["2024-01-01", "2024-01-01"],
        "HomeTeam": ["A", "A"],
        "AwayTeam": ["B", "B"],
        "home_xg": [1.0, 1.1],
        "away_xg": [0.8, 0.9],
    })

    assert validate_xg_dataframe(df)["duplicate_identity_count"] == 1


def test_schema_valid_template_is_contract_ready_but_not_production_ready():
    df = pd.DataFrame({"Date": ["2024-01-01"], "HomeTeam": ["A"], "AwayTeam": ["B"], "home_xg": [1.0], "away_xg": [0.8]})

    summary = validate_xg_dataframe(df, path="xg_raw_template.csv")

    assert summary["xg_contract_ready"] is True
    assert summary["xg_file_role"] == "TEMPLATE_OR_SAMPLE"
    assert summary["xg_production_ready"] is False


def test_tiny_xg_clean_demo_file_is_not_production_ready():
    df = pd.DataFrame({
        "Date": ["2024-01-01", "2024-01-02"],
        "HomeTeam": ["A", "C"],
        "AwayTeam": ["B", "D"],
        "home_xg": [1.0, 1.2],
        "away_xg": [0.8, 0.9],
    })

    summary = validate_xg_dataframe(df, path="xg_clean.csv")

    assert summary["xg_contract_ready"] is True
    assert summary["xg_production_ready"] is False


def test_production_ready_xg_file_triggers_ready_recommendation(tmp_path):
    root = tmp_path / "repo"
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    rows = 8
    pd.DataFrame({
        "Date": [f"2024-01-{day:02d}" for day in range(1, rows + 1)],
        "HomeTeam": [f"H{day}" for day in range(rows)],
        "AwayTeam": [f"A{day}" for day in range(rows)],
        "home_xg": [1.0] * rows,
        "away_xg": [0.8] * rows,
    }).to_csv(raw / "season_xg_enrichment.csv", index=False)

    table, _markdown = xg_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    assert table["xg_production_ready"].astype(bool).any()
    assert xg_audit.recommendation(table) == "READY_FOR_XG_CSV_IMPORTER"


def test_only_template_xg_files_do_not_recommend_ready_importer(tmp_path):
    root = tmp_path / "repo"
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    pd.DataFrame({"Date": ["2024-01-01"], "HomeTeam": ["A"], "AwayTeam": ["B"], "home_xg": [1.0], "away_xg": [0.8]}).to_csv(raw / "xg_raw_template.csv", index=False)

    table, _markdown = xg_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    assert table["xg_contract_ready"].astype(bool).any()
    assert not table["xg_production_ready"].astype(bool).any()
    assert xg_audit.recommendation(table) == "ADD_MANUAL_XG_CSV_FILES"


def test_data_audit_and_repair_plan_match_no_production_xg_condition(tmp_path):
    root = tmp_path / "repo"
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    pd.DataFrame({
        "Date": ["2024-01-01"],
        "HomeTeam": ["A"],
        "AwayTeam": ["B"],
        "FTHG": [1],
        "FTAG": [0],
        "FTR": ["H"],
        "B365H": [2.0],
        "B365D": [3.0],
        "B365A": [4.0],
    }).to_csv(raw / "football_data_E0_2024.csv", index=False)
    pd.DataFrame({"Date": ["2024-01-01"], "HomeTeam": ["A"], "AwayTeam": ["B"], "home_xg": [1.0], "away_xg": [0.8]}).to_csv(raw / "xg_raw_template.csv", index=False)

    xg_table, _xg_md = xg_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")
    data_table, _data_md = data_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")
    plan, _plan_md = repair_plan.run(base_root=root, output_dir=root / "outputs" / "diagnostics")

    assert xg_audit.recommendation(xg_table) == "ADD_MANUAL_XG_CSV_FILES"
    assert data_audit.recommendation(data_table) == "READY_FOR_IMPORTER_IMPLEMENTATION"
    assert repair_plan.recommendation(plan) == "ADD_XG_ENRICHMENT_FILES"


def test_normalize_xg_column_names_does_not_mutate_original_df():
    df = pd.DataFrame({"xG_home": [1.0], "xG_away": [0.8]})
    normalized = normalize_xg_column_names(df)

    assert list(df.columns) == ["xG_home", "xG_away"]
    assert list(normalized.columns) == ["home_xg", "away_xg"]


def test_xg_audit_script_writes_csv_and_markdown(tmp_path):
    root = tmp_path / "repo"
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    pd.DataFrame({"Date": ["2024-01-01"], "HomeTeam": ["A"], "AwayTeam": ["B"], "home_xg": [1.0], "away_xg": [0.8]}).to_csv(raw / "manual_xg.csv", index=False)
    output_dir = root / "outputs" / "diagnostics"

    table, markdown = xg_audit.run(root=root, output_dir=output_dir)

    assert len(table) == 1
    assert (output_dir / xg_audit.OUTPUT_CSV).exists()
    assert (output_dir / xg_audit.OUTPUT_MD).exists()
    assert "Phase 12.6 is diagnostic/foundation only" in markdown


def test_importer_registry_includes_manual_xg_and_placeholders():
    assert get_importer("manual_xg_csv")["status"] == "ACTIVE"
    assert get_importer("fbref_xg_csv")["status"] == "PLACEHOLDER"
    assert get_importer("understat_xg_csv_placeholder")["status"] == "PLACEHOLDER"


def test_script_does_not_modify_protected_logic_files(tmp_path):
    protected = [
        ROOT / "src/football_prediction_v19/diagnostics/market_tier.py",
        ROOT / "src/football_prediction_v19/diagnostics/recommended_market.py",
        ROOT / "src/football_prediction_v19/model.py",
    ]
    before = {path: _hash(path) for path in protected}
    root = tmp_path / "repo"
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    pd.DataFrame({"Date": ["2024-01-01"], "HomeTeam": ["A"], "AwayTeam": ["B"], "home_xg": [1.0], "away_xg": [0.8]}).to_csv(raw / "manual_xg.csv", index=False)

    xg_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    after = {path: _hash(path) for path in protected}
    assert after == before
