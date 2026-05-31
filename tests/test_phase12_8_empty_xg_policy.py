# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

from football_prediction_v19.data_repair import build_repair_plan_for_dataframe
from football_prediction_v19.xg_enrichment import summarize_xg_coverage
from football_prediction_v19.xg_partial_attribution import build_partial_xg_attribution_for_dataframe
from football_prediction_v19.xg_policy import (
    ALLOW_EMPTY_XG_PLACEHOLDERS,
    REQUIRE_PRODUCTION_XG_VALUES,
    XG_PLACEHOLDER_EMPTY,
    XG_PRODUCTION_READY,
    apply_empty_xg_policy_to_summary,
    classify_xg_policy_status,
    is_xg_placeholder,
    is_xg_usable_for_model,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_partial_xg_sources as partial_audit  # noqa: E402
import audit_xg_enrichment_contracts as xg_audit  # noqa: E402
import audit_data_contracts as data_audit  # noqa: E402
import plan_data_contract_repairs as repair_plan  # noqa: E402
import write_xg_policy_register as policy_register  # noqa: E402


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _empty_processed() -> pd.DataFrame:
    return pd.DataFrame({"date": ["2024-01-01"], "home_team": ["A"], "away_team": ["B"], "home_xg": [None], "away_xg": [None]})


def _historical() -> pd.DataFrame:
    return pd.DataFrame({
        "Date": ["2024-01-01"],
        "HomeTeam": ["A"],
        "AwayTeam": ["B"],
        "FTHG": [1],
        "FTAG": [0],
        "FTR": ["H"],
        "B365H": [2.0],
        "B365D": [3.0],
        "B365A": [4.0],
    })


def _real_null_xg(rows: int = 5) -> pd.DataFrame:
    return pd.DataFrame({
        "Date": [f"2024-01-{day:02d}" for day in range(1, rows + 1)],
        "HomeTeam": [f"H{day}" for day in range(rows)],
        "AwayTeam": [f"A{day}" for day in range(rows)],
        "home_xg": [None] * rows,
        "away_xg": [0.8] * rows,
    })


def test_all_null_processed_xg_columns_become_placeholder_empty():
    df = _empty_processed()
    summary = summarize_xg_coverage(df, path="data/processed/features_clean.csv")

    assert summary["xg_policy_status"] == XG_PLACEHOLDER_EMPTY
    assert summary["xg_placeholder"] is True


def test_xg_placeholder_empty_is_not_usable_for_model():
    assert is_xg_usable_for_model(XG_PLACEHOLDER_EMPTY) is False
    assert is_xg_placeholder(XG_PLACEHOLDER_EMPTY) is True


def test_xg_placeholder_empty_non_blocking_under_allow_policy():
    summary = {"xg_policy_status": XG_PLACEHOLDER_EMPTY}

    out = apply_empty_xg_policy_to_summary(summary, policy=ALLOW_EMPTY_XG_PLACEHOLDERS)

    assert out["xg_policy_blocking"] is False


def test_xg_placeholder_empty_blocking_under_require_policy():
    summary = {"xg_policy_status": XG_PLACEHOLDER_EMPTY}

    out = apply_empty_xg_policy_to_summary(summary, policy=REQUIRE_PRODUCTION_XG_VALUES)

    assert out["xg_policy_blocking"] is True


def test_production_ready_xg_remains_usable_for_model():
    df = pd.DataFrame({
        "Date": [f"2024-01-{day:02d}" for day in range(1, 6)],
        "HomeTeam": [f"H{day}" for day in range(5)],
        "AwayTeam": [f"A{day}" for day in range(5)],
        "home_xg": [1.0] * 5,
        "away_xg": [0.8] * 5,
    })
    status = classify_xg_policy_status("season_xg_source.csv", df)

    assert status == XG_PRODUCTION_READY
    assert is_xg_usable_for_model(status) is True


def test_template_sample_xg_is_not_production_ready():
    df = pd.DataFrame({"Date": ["2024-01-01"], "HomeTeam": ["A"], "AwayTeam": ["B"], "home_xg": [1.0], "away_xg": [0.8]})
    summary = summarize_xg_coverage(df, path="xg_template.csv")

    assert summary["xg_policy_status"] == "XG_TEMPLATE_OR_SAMPLE"
    assert summary["xg_production_ready"] is False


def test_partial_attribution_no_longer_recommends_define_policy_when_placeholders_accepted(tmp_path):
    root = tmp_path / "repo"
    processed = root / "data" / "processed"
    processed.mkdir(parents=True)
    _empty_processed().to_csv(processed / "features_clean.csv", index=False)

    table, _markdown = partial_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    assert partial_audit.recommendation(table) != "DEFINE_EMPTY_XG_COLUMN_POLICY"
    assert table.iloc[0]["blocking"] == False


def test_repair_plan_marks_empty_xg_placeholders_low_risk_non_blocking():
    action = build_repair_plan_for_dataframe("data/processed/features_clean.csv", _empty_processed())[0]

    assert action.risk_level == "LOW"
    assert action.blocking is False
    assert action.xg_policy_status == XG_PLACEHOLDER_EMPTY
    assert action.xg_placeholder is True


def test_accepted_empty_placeholders_do_not_trigger_fix_partial(tmp_path):
    root = tmp_path / "repo"
    processed = root / "data" / "processed"
    processed.mkdir(parents=True)
    _empty_processed().to_csv(processed / "features_clean.csv", index=False)

    xg_table, _ = xg_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")
    data_table, _ = data_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")
    plan, _ = repair_plan.run(base_root=root, output_dir=root / "outputs" / "diagnostics")

    assert xg_audit.recommendation(xg_table) != "FIX_PARTIAL_XG_FILES_FIRST"
    assert data_audit.recommendation(data_table) != "FIX_PARTIAL_XG_FILES_FIRST"
    assert repair_plan.recommendation(plan) != "FIX_PARTIAL_XG_FILES_FIRST"


def test_xg_audit_recommends_add_manual_values_for_real_null_xg(tmp_path):
    root = tmp_path / "repo"
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    _real_null_xg().to_csv(raw / "season_xg_source.csv", index=False)

    table, _ = xg_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    assert xg_audit.recommendation(table) == "ADD_MANUAL_XG_VALUES"


def test_data_contract_audit_recommends_add_manual_values_for_real_null_xg(tmp_path):
    root = tmp_path / "repo"
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    _historical().to_csv(raw / "football_data_E0_2024.csv", index=False)
    _real_null_xg().to_csv(raw / "season_xg_source.csv", index=False)

    table, _ = data_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    assert data_audit.recommendation(table) == "ADD_MANUAL_XG_VALUES"


def test_repair_plan_recommends_add_manual_values_for_real_null_xg(tmp_path):
    root = tmp_path / "repo"
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    _historical().to_csv(raw / "football_data_E0_2024.csv", index=False)
    _real_null_xg().to_csv(raw / "season_xg_source.csv", index=False)

    plan, _ = repair_plan.run(base_root=root, output_dir=root / "outputs" / "diagnostics")

    assert repair_plan.recommendation(plan) == "ADD_MANUAL_XG_VALUES"


def test_only_placeholders_and_templates_are_not_fix_partial(tmp_path):
    root = tmp_path / "repo"
    processed = root / "data" / "processed"
    raw = root / "data" / "raw"
    processed.mkdir(parents=True)
    raw.mkdir(parents=True)
    _empty_processed().to_csv(processed / "features_clean.csv", index=False)
    pd.DataFrame({"Date": ["2024-01-01"], "Home": ["A"], "Away": ["B"], "xG": [1.0]}).to_csv(raw / "fbref_xg_template.csv", index=False)

    table, _ = xg_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    assert xg_audit.recommendation(table) != "FIX_PARTIAL_XG_FILES_FIRST"


def test_policy_register_writes_csv_and_markdown(tmp_path):
    output_dir = tmp_path / "outputs" / "diagnostics"

    table, markdown = policy_register.run(output_dir=output_dir)

    assert not table.empty
    assert (output_dir / policy_register.OUTPUT_CSV).exists()
    assert (output_dir / policy_register.OUTPUT_MD).exists()
    assert ALLOW_EMPTY_XG_PLACEHOLDERS in markdown


def test_reports_say_no_xg_values_modified(tmp_path):
    root = tmp_path / "repo"
    processed = root / "data" / "processed"
    processed.mkdir(parents=True)
    _empty_processed().to_csv(processed / "features_clean.csv", index=False)

    _table, markdown = partial_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")
    _register, register_md = policy_register.run(output_dir=root / "outputs" / "diagnostics")

    assert "No xG values were inferred, invented, deleted, or modified" in markdown
    assert "No xG values invented/deleted/modified" in register_md


def test_script_does_not_modify_protected_logic_files(tmp_path):
    protected = [
        ROOT / "src/football_prediction_v19/diagnostics/market_tier.py",
        ROOT / "src/football_prediction_v19/diagnostics/recommended_market.py",
        ROOT / "src/football_prediction_v19/model.py",
    ]
    before = {path: _hash(path) for path in protected}
    output_dir = tmp_path / "outputs" / "diagnostics"

    policy_register.run(output_dir=output_dir)

    after = {path: _hash(path) for path in protected}
    assert after == before
