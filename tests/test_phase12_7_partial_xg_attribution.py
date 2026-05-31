# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

from football_prediction_v19.xg_partial_attribution import (
    EMPTY_XG_COLUMNS_IN_PROCESSED_FEATURES,
    FBREF_IDENTITY_MAPPING_MISSING,
    FIXTURE_FILE_MISSING_XG_PAIR,
    ODDS_FILE_NOT_XG_SOURCE,
    REAL_XG_SOURCE_WITH_NEGATIVE_VALUES,
    REAL_XG_SOURCE_WITH_NULL_VALUES,
    SAMPLE_OR_DEMO_PARTIAL_XG,
    TEMPLATE_PARTIAL_XG,
    UNDERSTAT_IDENTITY_MAPPING_MISSING,
    build_partial_xg_attribution_for_dataframe,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_partial_xg_sources as partial_audit  # noqa: E402


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_processed_feature_all_null_xg_columns_gets_cleanup_policy():
    df = pd.DataFrame({"date": ["2024-01-01"], "home_team": ["A"], "away_team": ["B"], "home_xg": [None], "away_xg": [None]})

    row = build_partial_xg_attribution_for_dataframe("data/processed/features_clean.csv", df)

    assert row["partial_xg_source_category"] == EMPTY_XG_COLUMNS_IN_PROCESSED_FEATURES
    assert row["partial_xg_decision"] == "NEEDS_XG_COLUMN_CLEANUP_POLICY"
    assert row["blocking"] is True


def test_template_partial_xg_is_non_blocking():
    df = pd.DataFrame({"Date": ["2024-01-01"], "Home": ["A"], "Away": ["B"], "xG": [1.0]})

    row = build_partial_xg_attribution_for_dataframe("fbref_xg_template.csv", df)

    assert row["partial_xg_source_category"] == TEMPLATE_PARTIAL_XG
    assert row["blocking"] is False


def test_sample_demo_partial_xg_is_non_blocking():
    df = pd.DataFrame({"date": ["2024-01-01"], "home_team": ["A"], "away_team": ["B"], "home_xg": [None], "away_xg": [None]})

    row = build_partial_xg_attribution_for_dataframe("sample_matches_with_xg.csv", df)

    assert row["partial_xg_source_category"] == SAMPLE_OR_DEMO_PARTIAL_XG
    assert row["blocking"] is False


def test_fixture_without_xg_pair_is_non_blocking_unless_filename_contains_xg():
    df = pd.DataFrame({"date": ["2024-01-01"], "home_team": ["A"], "away_team": ["B"]})

    normal = build_partial_xg_attribution_for_dataframe("upcoming_fixtures.csv", df)
    explicit = build_partial_xg_attribution_for_dataframe("upcoming_fixtures_xg.csv", df)

    assert normal["partial_xg_source_category"] == FIXTURE_FILE_MISSING_XG_PAIR
    assert normal["blocking"] is False
    assert explicit["partial_xg_source_category"] == FIXTURE_FILE_MISSING_XG_PAIR
    assert explicit["blocking"] is True


def test_odds_file_without_xg_pair_is_non_blocking():
    df = pd.DataFrame({"date": ["2024-01-01"], "home_team": ["A"], "away_team": ["B"], "odds_home": [2.0], "odds_draw": [3.0], "odds_away": [4.0]})

    row = build_partial_xg_attribution_for_dataframe("market_odds.csv", df)

    assert row["partial_xg_source_category"] == ODDS_FILE_NOT_XG_SOURCE
    assert row["blocking"] is False


def test_fbref_missing_identity_mapping_detected():
    df = pd.DataFrame({"Date": ["2024-01-01"], "xG": [1.0], "xGA": [0.8]})

    row = build_partial_xg_attribution_for_dataframe("mls_fbref_raw.csv", df)

    assert row["partial_xg_source_category"] == FBREF_IDENTITY_MAPPING_MISSING
    assert row["partial_xg_decision"] == "NEEDS_FBREF_MAPPING"


def test_understat_missing_identity_mapping_detected():
    df = pd.DataFrame({"xg": [1.0], "xga": [0.8]})

    row = build_partial_xg_attribution_for_dataframe("understat_xg.csv", df)

    assert row["partial_xg_source_category"] == UNDERSTAT_IDENTITY_MAPPING_MISSING
    assert row["partial_xg_decision"] == "NEEDS_UNDERSTAT_MAPPING"


def test_real_xg_source_with_null_values_is_blocking():
    df = pd.DataFrame({"Date": ["2024-01-01"], "HomeTeam": ["A"], "AwayTeam": ["B"], "home_xg": [None], "away_xg": [0.8]})

    row = build_partial_xg_attribution_for_dataframe("season_xg_source.csv", df)

    assert row["partial_xg_source_category"] == REAL_XG_SOURCE_WITH_NULL_VALUES
    assert row["blocking"] is True


def test_negative_xg_values_are_manual_review_blocking():
    df = pd.DataFrame({"Date": ["2024-01-01"], "HomeTeam": ["A"], "AwayTeam": ["B"], "home_xg": [-0.2], "away_xg": [0.8]})

    row = build_partial_xg_attribution_for_dataframe("season_xg_source.csv", df)

    assert row["partial_xg_source_category"] == REAL_XG_SOURCE_WITH_NEGATIVE_VALUES
    assert row["partial_xg_decision"] == "MANUAL_REVIEW_REQUIRED"
    assert row["blocking"] is True


def test_recommendation_define_empty_xg_column_policy(tmp_path):
    root = tmp_path / "repo"
    processed = root / "data" / "processed"
    processed.mkdir(parents=True)
    pd.DataFrame({"date": ["2024-01-01"], "home_team": ["A"], "away_team": ["B"], "home_xg": [None], "away_xg": [None]}).to_csv(processed / "features_clean.csv", index=False)

    table, _markdown = partial_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    assert partial_audit.recommendation(table) == "DEFINE_EMPTY_XG_COLUMN_POLICY"


def test_recommendation_ready_when_only_templates_or_samples_are_partial(tmp_path):
    root = tmp_path / "repo"
    raw = root / "data" / "raw"
    raw.mkdir(parents=True)
    pd.DataFrame({"Date": ["2024-01-01"], "Home": ["A"], "Away": ["B"], "xG": [1.0]}).to_csv(raw / "fbref_xg_template.csv", index=False)

    table, _markdown = partial_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    assert partial_audit.recommendation(table) == "READY_FOR_XG_IMPORTER_SKELETONS"


def test_script_writes_csv_and_markdown(tmp_path):
    root = tmp_path / "repo"
    processed = root / "data" / "processed"
    processed.mkdir(parents=True)
    pd.DataFrame({"date": ["2024-01-01"], "home_team": ["A"], "away_team": ["B"], "home_xg": [None], "away_xg": [None]}).to_csv(processed / "features_clean.csv", index=False)
    output_dir = root / "outputs" / "diagnostics"

    table, markdown = partial_audit.run(root=root, output_dir=output_dir)

    assert len(table) == 1
    assert (output_dir / partial_audit.OUTPUT_CSV).exists()
    assert (output_dir / partial_audit.OUTPUT_MD).exists()
    assert "No xG values were inferred, invented, deleted, or modified" in markdown


def test_script_does_not_modify_protected_logic_files(tmp_path):
    protected = [
        ROOT / "src/football_prediction_v19/diagnostics/market_tier.py",
        ROOT / "src/football_prediction_v19/diagnostics/recommended_market.py",
        ROOT / "src/football_prediction_v19/model.py",
    ]
    before = {path: _hash(path) for path in protected}
    root = tmp_path / "repo"
    processed = root / "data" / "processed"
    processed.mkdir(parents=True)
    pd.DataFrame({"date": ["2024-01-01"], "home_team": ["A"], "away_team": ["B"], "home_xg": [None], "away_xg": [None]}).to_csv(processed / "features_clean.csv", index=False)

    partial_audit.run(root=root, output_dir=root / "outputs" / "diagnostics")

    after = {path: _hash(path) for path in protected}
    assert after == before
