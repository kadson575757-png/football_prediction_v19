# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

from football_prediction_v19.data_repair import (
    RepairAction,
    build_repair_plan_for_dataframe,
    safe_preview_output_path,
    write_repair_preview,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import plan_data_contract_repairs as planner  # noqa: E402


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


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _categories(actions):
    return {action.issue_category for action in actions}


def test_invalid_historical_score_creates_high_risk_action():
    actions = build_repair_plan_for_dataframe("football_data_E0_2024.csv", _historical(FTHG=[1, -1]))

    action = next(a for a in actions if a.issue_category == "HISTORICAL_INVALID_SCORE")
    assert action.risk_level == "HIGH"


def test_invalid_ftr_creates_high_risk_action():
    actions = build_repair_plan_for_dataframe("football_data_E0_2024.csv", _historical(FTR=["H", "X"]))

    action = next(a for a in actions if a.issue_category == "HISTORICAL_INVALID_RESULT")
    assert action.risk_level == "HIGH"


def test_date_parse_failure_creates_medium_risk_action():
    actions = build_repair_plan_for_dataframe("football_data_E0_2024.csv", _historical(Date=["not-a-date", "2024-08-02"]))

    action = next(a for a in actions if a.issue_category == "HISTORICAL_DATE_PARSE_FAILURE")
    assert action.risk_level == "MEDIUM"


def test_blank_team_creates_high_risk_action():
    actions = build_repair_plan_for_dataframe("football_data_E0_2024.csv", _historical(HomeTeam=["", "B"]))

    action = next(a for a in actions if a.issue_category == "HISTORICAL_BLANK_TEAM")
    assert action.risk_level == "HIGH"


def test_empty_fixture_creates_low_risk_action():
    df = pd.DataFrame(columns=["date", "home_team", "away_team"])
    actions = build_repair_plan_for_dataframe("upcoming_fixtures.csv", df)

    action = actions[0]
    assert action.issue_category == "EMPTY_FIXTURE_FILE"
    assert action.risk_level == "LOW"


def test_unknown_csv_creates_unknown_type_manual_action():
    actions = build_repair_plan_for_dataframe("misc.csv", pd.DataFrame({"foo": [1]}))

    assert actions[0].issue_category == "UNKNOWN_CSV_TYPE"
    assert actions[0].auto_repair_supported is False


def test_template_creates_template_only_no_action():
    actions = build_repair_plan_for_dataframe("matches_template.csv", pd.DataFrame({"foo": [1]}))

    assert actions[0].issue_category == "TEMPLATE_ONLY_NO_ACTION"


def test_processed_feature_creates_processed_feature_no_action():
    actions = build_repair_plan_for_dataframe("data/processed/features_clean.csv", pd.DataFrame({"date": ["2024-01-01"]}))

    assert actions[0].issue_category == "PROCESSED_FEATURE_NO_ACTION"


def test_ready_historical_creates_ready_no_action_when_available():
    actions = build_repair_plan_for_dataframe("football_data_E0_2024.csv", _historical(B365H=[2.0, 2.1], B365D=[3.0, 3.1], B365A=[4.0, 4.1]))

    assert "READY_NO_ACTION" in _categories(actions)


def test_safe_preview_output_path_never_equals_source_path(tmp_path):
    source = tmp_path / "source.csv"
    source.write_text("a\n1\n", encoding="utf-8")
    preview = safe_preview_output_path(source, tmp_path / "outputs" / "repair_preview")

    assert preview.resolve() != source.resolve()
    assert "repair_preview" in str(preview)


def test_write_repair_preview_writes_only_under_repair_preview(tmp_path):
    source = tmp_path / "source.csv"
    source.write_text("a\n1\n", encoding="utf-8")
    output_dir = tmp_path / "outputs" / "repair_preview"
    action = RepairAction(
        file_path=str(source),
        file_name=source.name,
        file_type="TEMPLATE_CSV",
        contract_quality_label="TEMPLATE_ONLY",
        issue_category="TEST_PREVIEW",
        issue_detail="test",
        recommended_action="preview copy",
        auto_repair_supported=True,
        preview_output_path="",
        risk_level="LOW",
    )

    preview = write_repair_preview(source, pd.DataFrame({"a": [1]}), action, output_dir)

    assert preview is not None
    assert output_dir.resolve() in preview.resolve().parents
    assert preview.resolve() != source.resolve()


def test_script_writes_repair_plan_csv_and_markdown(tmp_path):
    root = tmp_path / "repo"
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    _historical(FTHG=[1, -1]).to_csv(raw / "football_data_E0_2024.csv", index=False)
    output_dir = root / "outputs" / "diagnostics"

    plan, markdown = planner.run(base_root=root, output_dir=output_dir)

    assert not plan.empty
    assert (output_dir / planner.OUTPUT_CSV).exists()
    assert (output_dir / planner.OUTPUT_MD).exists()
    assert "Phase 12.3 is diagnostic/foundation only" in markdown


def test_script_default_does_not_write_preview_files(tmp_path):
    root = tmp_path / "repo"
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    _historical(FTHG=[1, -1]).to_csv(raw / "football_data_E0_2024.csv", index=False)
    preview_dir = root / "outputs" / "repair_preview"

    planner.run(base_root=root, output_dir=root / "outputs" / "diagnostics", repair_preview_dir=preview_dir)

    assert not preview_dir.exists()


def test_write_preview_writes_only_for_supported_low_risk_actions_if_any(tmp_path):
    root = tmp_path / "repo"
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    pd.DataFrame({"foo": [1]}).to_csv(raw / "matches_template.csv", index=False)
    preview_dir = root / "outputs" / "repair_preview"

    plan, _markdown = planner.run(
        base_root=root,
        output_dir=root / "outputs" / "diagnostics",
        repair_preview_dir=preview_dir,
        write_preview=True,
    )

    assert "TEMPLATE_ONLY_NO_ACTION" in set(plan["issue_category"])
    assert not preview_dir.exists()


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
    _historical(FTHG=[1, -1]).to_csv(raw / "football_data_E0_2024.csv", index=False)

    planner.run(base_root=root, output_dir=root / "outputs" / "diagnostics")

    after = {path: _hash(path) for path in protected}
    assert after == before
