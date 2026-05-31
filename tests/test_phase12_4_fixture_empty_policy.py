# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

from football_prediction_v19.data_contracts import summarize_data_quality_by_file_type
from football_prediction_v19.data_repair import build_repair_plan_for_dataframe
from football_prediction_v19.fixture_policy import (
    EMPTY_FIXTURE_NEEDS_REFRESH,
    EMPTY_FIXTURE_OK,
    FIXTURE_CONTRACT_INVALID,
    FIXTURE_READY,
    NOT_A_FIXTURE_FILE,
    classify_fixture_status,
    is_fixture_status_blocking,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_data_contracts as audit  # noqa: E402
import plan_data_contract_repairs as planner  # noqa: E402


def _historical() -> pd.DataFrame:
    return pd.DataFrame({
        "Date": ["2024-08-01"],
        "HomeTeam": ["A"],
        "AwayTeam": ["B"],
        "FTHG": [1],
        "FTAG": [0],
        "FTR": ["H"],
        "B365H": [2.0],
        "B365D": [3.0],
        "B365A": [4.0],
    })


def _fixture(rows: int = 1) -> pd.DataFrame:
    data = {
        "date": ["2024-08-10"] * rows,
        "home_team": ["A"] * rows,
        "away_team": ["B"] * rows,
    }
    return pd.DataFrame(data)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_non_fixture_returns_not_a_fixture_file():
    status = classify_fixture_status("football_data_E0_2024.csv", _historical())

    assert status == NOT_A_FIXTURE_FILE


def test_valid_fixture_rows_return_fixture_ready():
    status = classify_fixture_status("fixtures.csv", _fixture())

    assert status == FIXTURE_READY


def test_fixture_rows_missing_identity_return_invalid():
    status = classify_fixture_status("fixtures.csv", pd.DataFrame({"team": ["A"]}))

    assert status == FIXTURE_CONTRACT_INVALID


def test_empty_upcoming_fixture_is_ok_by_default():
    status = classify_fixture_status("upcoming_fixtures.csv", _fixture(0))

    assert status == EMPTY_FIXTURE_OK


def test_empty_upcoming_fixture_can_require_refresh_when_not_allowed():
    status = classify_fixture_status("upcoming_fixtures.csv", _fixture(0), allow_empty_upcoming=False)

    assert status == EMPTY_FIXTURE_NEEDS_REFRESH


def test_empty_non_upcoming_fixture_requires_refresh():
    status = classify_fixture_status("fixtures.csv", _fixture(0))

    assert status == EMPTY_FIXTURE_NEEDS_REFRESH


def test_empty_fixture_ok_is_non_blocking():
    assert is_fixture_status_blocking(EMPTY_FIXTURE_OK) is False


def test_empty_fixture_needs_refresh_is_blocking():
    assert is_fixture_status_blocking(EMPTY_FIXTURE_NEEDS_REFRESH) is True


def test_summary_includes_fixture_status_fields():
    summary = summarize_data_quality_by_file_type("upcoming_fixtures.csv", _fixture(0))

    assert summary["contract_quality_label"] == EMPTY_FIXTURE_OK
    assert summary["fixture_status"] == EMPTY_FIXTURE_OK
    assert summary["fixture_status_blocking"] is False
    assert "allowed by policy" in summary["fixture_status_reason"]


def test_audit_recommendation_not_fixture_first_when_only_empty_fixture_ok(tmp_path):
    root = tmp_path / "repo"
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    _historical().to_csv(raw / "football_data_E0_2024.csv", index=False)
    _fixture(0).to_csv(raw / "upcoming_fixtures.csv", index=False)

    table, markdown = audit.run(root=root, output_dir=root / "outputs" / "diagnostics")
    rec = audit.recommendation(table)

    assert rec != "FIX_FIXTURE_CONTRACTS_FIRST"
    assert rec == "READY_FOR_IMPORTER_IMPLEMENTATION"
    assert "Fixture Empty-File Policy" in markdown
    assert EMPTY_FIXTURE_OK in markdown


def test_repair_plan_marks_empty_fixture_ok_non_blocking():
    action = build_repair_plan_for_dataframe("upcoming_fixtures.csv", _fixture(0))[0]

    assert action.issue_category == "EMPTY_FIXTURE_FILE"
    assert action.fixture_status == EMPTY_FIXTURE_OK
    assert action.blocking is False
    assert "no repair required" in action.recommended_action


def test_repair_plan_recommendation_not_empty_fixture_first_when_only_empty_ok(tmp_path):
    root = tmp_path / "repo"
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    _fixture(0).to_csv(raw / "upcoming_fixtures.csv", index=False)

    plan, markdown = planner.run(base_root=root, output_dir=root / "outputs" / "diagnostics")
    rec = planner.recommendation(plan)

    assert rec != "FIX_EMPTY_FIXTURE_FILES_FIRST"
    assert "Empty Fixture Files Allowed by Policy" in markdown
    assert EMPTY_FIXTURE_OK in markdown


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
    _historical().to_csv(raw / "football_data_E0_2024.csv", index=False)
    _fixture(0).to_csv(raw / "upcoming_fixtures.csv", index=False)

    audit.run(root=root, output_dir=root / "outputs" / "diagnostics")
    planner.run(base_root=root, output_dir=root / "outputs" / "diagnostics")

    after = {path: _hash(path) for path in protected}
    assert after == before
