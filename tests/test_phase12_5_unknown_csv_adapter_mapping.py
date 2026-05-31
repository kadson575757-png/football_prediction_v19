# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

from football_prediction_v19.csv_adapter_mapping import (
    DAILY_FIXTURE_ANALYSIS_CSV,
    FBREF_MATCH_STATS_CSV,
    FINAL_SCORES_CSV,
    MLS_MATCHES_CSV,
    SAMPLE_ANALYSIS_INPUT_CSV,
    get_adapter_mapping_for_file,
    summarize_adapter_mapping,
)
from football_prediction_v19.data_contracts import classify_csv_file, summarize_data_quality_by_file_type
from football_prediction_v19.data_repair import build_repair_plan_for_dataframe


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_data_contracts as audit  # noqa: E402
import plan_data_contract_repairs as planner  # noqa: E402


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _fbref() -> pd.DataFrame:
    return pd.DataFrame({
        "Date": ["2024-08-01"],
        "Home": ["A"],
        "Away": ["B"],
        "xG": [1.1],
        "xG.1": [0.8],
        "Venue": ["Home"],
    })


def _mls_matches() -> pd.DataFrame:
    return pd.DataFrame({
        "date": ["2024-08-01"],
        "home_team": ["A"],
        "away_team": ["B"],
        "home_xg": [1.2],
        "away_xg": [0.7],
        "odds_home": [2.0],
        "odds_draw": [3.0],
        "odds_away": [4.0],
    })


def _daily_fixture() -> pd.DataFrame:
    return pd.DataFrame({
        "date": ["2024-08-02"],
        "home_team": ["A"],
        "away_team": ["B"],
        "league": ["Serie A"],
        "odds_home": [2.0],
        "odds_draw": [3.0],
        "odds_away": [4.0],
    })


def _final_scores() -> pd.DataFrame:
    return pd.DataFrame({
        "date": ["2024-08-03"],
        "home_team": ["A"],
        "away_team": ["B"],
        "home_goals": [1],
        "away_goals": [0],
    })


def _sample_matches() -> pd.DataFrame:
    return pd.DataFrame({
        "Date": ["2024-08-04"],
        "Home": ["A"],
        "Away": ["B"],
        "xG": [1.4],
        "xG.1": [0.9],
        "odds_home": [2.0],
        "odds_draw": [3.0],
        "odds_away": [4.0],
    })


def test_mls_fbref_raw_maps_to_fbref_match_stats():
    mapping = get_adapter_mapping_for_file("mls_fbref_raw.csv", list(_fbref().columns))

    assert mapping is not None
    assert mapping["adapter_type"] == FBREF_MATCH_STATS_CSV


def test_mls_matches_maps_to_mls_matches():
    assert get_adapter_mapping_for_file("mls_matches.csv", list(_mls_matches().columns))["adapter_type"] == MLS_MATCHES_CSV


def test_seriea_today_maps_to_daily_fixture_analysis():
    assert get_adapter_mapping_for_file("seriea_today.csv", list(_daily_fixture().columns))["adapter_type"] == DAILY_FIXTURE_ANALYSIS_CSV


def test_final_scores_maps_to_final_scores():
    assert get_adapter_mapping_for_file("final_scores.csv", list(_final_scores().columns))["adapter_type"] == FINAL_SCORES_CSV


def test_sample_matches_maps_to_sample_analysis_input():
    assert get_adapter_mapping_for_file("sample_matches.csv", list(_sample_matches().columns))["adapter_type"] == SAMPLE_ANALYSIS_INPUT_CSV


def test_adapter_mapped_csv_is_not_hard_unknown():
    assert classify_csv_file("mls_fbref_raw.csv", list(_fbref().columns)) == "ADAPTER_MAPPED_CSV"
    assert classify_csv_file("final_scores.csv", list(_final_scores().columns)) == "ADAPTER_MAPPED_CSV"


def test_adapter_summary_includes_intended_use_and_replay_source():
    summary = summarize_adapter_mapping("mls_matches.csv", _mls_matches())

    assert summary["adapter_type"] == MLS_MATCHES_CSV
    assert summary["adapter_readiness"] == "ADAPTER_READY"
    assert "MLS processed" in summary["intended_use"]
    assert summary["replay_source"] is False


def test_daily_fixture_analysis_csv_can_be_fixture_ready_without_scores():
    summary = summarize_data_quality_by_file_type("seriea_today.csv", _daily_fixture())

    assert summary["file_type"] == "FIXTURE_CSV"
    assert summary["contract_quality_label"] == "READY_FOR_FIXTURES"
    assert summary["adapter_type"] == DAILY_FIXTURE_ANALYSIS_CSV


def test_final_scores_csv_is_not_replay_ready_until_normalized():
    summary = summarize_data_quality_by_file_type("final_scores.csv", _final_scores())

    assert summary["file_type"] == "ADAPTER_MAPPED_CSV"
    assert summary["contract_quality_label"] == "ADAPTER_READY"
    assert summary["replay_ready"] is False


def test_data_contract_audit_includes_adapter_fields(tmp_path):
    root = tmp_path / "repo"
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    _historical().to_csv(raw / "football_data_E0_2024.csv", index=False)
    _fbref().to_csv(raw / "mls_fbref_raw.csv", index=False)

    table, markdown = audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    row = table[table["file_name"] == "mls_fbref_raw.csv"].iloc[0]
    assert row["adapter_type"] == FBREF_MATCH_STATS_CSV
    assert row["adapter_readiness"] == "ADAPTER_READY"
    assert "Adapter-Mapped CSV Files" in markdown


def test_repair_plan_treats_adapter_mapped_csv_as_non_blocking():
    action = build_repair_plan_for_dataframe("mls_fbref_raw.csv", _fbref())[0]

    assert action.issue_category == "ADAPTER_MAPPED_NO_ACTION"
    assert action.risk_level == "LOW"
    assert action.blocking is False


def test_recommendation_moves_away_from_classify_unknown_when_unknown_files_are_mapped(tmp_path):
    root = tmp_path / "repo"
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    _historical().to_csv(raw / "football_data_E0_2024.csv", index=False)
    _fbref().to_csv(raw / "mls_fbref_raw.csv", index=False)
    _mls_matches().to_csv(raw / "mls_matches.csv", index=False)
    _daily_fixture().to_csv(raw / "seriea_today.csv", index=False)
    _final_scores().to_csv(root / "data" / "final_scores.csv", index=False)
    _sample_matches().to_csv(root / "data" / "sample_matches.csv", index=False)

    table, _markdown = audit.run(root=root, output_dir=root / "outputs" / "diagnostics")
    plan, _plan_md = planner.run(base_root=root, output_dir=root / "outputs" / "diagnostics")

    assert "UNKNOWN_CSV" not in set(table["file_type"])
    assert audit.recommendation(table) != "CLASSIFY_UNKNOWN_CSV_FILES"
    assert planner.recommendation(plan) != "CLASSIFY_UNKNOWN_CSV_FILES"


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
    _fbref().to_csv(raw / "mls_fbref_raw.csv", index=False)

    audit.run(root=root, output_dir=root / "outputs" / "diagnostics")
    planner.run(base_root=root, output_dir=root / "outputs" / "diagnostics")

    after = {path: _hash(path) for path in protected}
    assert after == before
