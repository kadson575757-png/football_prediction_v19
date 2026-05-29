# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import analyze_tier_rule_candidates as analysis  # noqa: E402


def _row(
    *,
    success=True,
    market_tier="A_TIER",
    ensemble_agreement="HIGH",
    warning="",
    strength="HIGH",
    subtype="UNDER_35",
    league="League A",
    chaos_bucket="low",
    ctrl_bucket="high",
    odds_bucket="mid",
    season_phase="mid",
) -> dict:
    return {
        "type_success": "" if success is None else success,
        "market_tier": market_tier,
        "ensemble_agreement": ensemble_agreement,
        "league_warning_flags": warning,
        "league_adjusted_strength": strength,
        "recommended_market_subtype": subtype,
        "league": league,
        "chaos_bucket": chaos_bucket,
        "ctrl_bucket": ctrl_bucket,
        "odds_bucket": odds_bucket,
        "season_phase": season_phase,
    }


def _rows(n: int, hits: int, **kwargs) -> list[dict]:
    return [_row(success=i < hits, **kwargs) for i in range(n)]


def _write_input(tmp_path: Path, rows: list[dict]) -> Path:
    input_dir = tmp_path / "season_replay"
    input_dir.mkdir()
    pd.DataFrame(rows).to_csv(input_dir / "synthetic_evaluation.csv", index=False)
    return input_dir


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_parses_boolean_type_success_correctly():
    assert analysis.parse_bool_success(True) is True
    assert analysis.parse_bool_success("1") is True
    assert analysis.parse_bool_success("yes") is True
    assert analysis.parse_bool_success(False) is False
    assert analysis.parse_bool_success("0") is False
    assert analysis.parse_bool_success("no") is False
    assert analysis.parse_bool_success("") is None


def test_excludes_blank_type_success_rows(tmp_path):
    input_dir = _write_input(tmp_path, [_row(success=True), _row(success=False), _row(success=None)])
    df = analysis.load_evaluation_rows(input_dir)

    assert len(df) == 2


def test_normalizes_blank_market_tier_to_unknown(tmp_path):
    input_dir = _write_input(tmp_path, [_row(market_tier="")])
    df = analysis.load_evaluation_rows(input_dir)

    assert df["market_tier"].iloc[0] == "UNKNOWN"


def test_normalizes_old_ensemble_labels(tmp_path):
    input_dir = _write_input(
        tmp_path,
        [
            _row(ensemble_agreement="CONSENSUS"),
            _row(ensemble_agreement="SPLIT"),
            _row(ensemble_agreement="DISAGREEMENT"),
            _row(ensemble_agreement=""),
        ],
    )
    df = analysis.load_evaluation_rows(input_dir)

    assert list(df["ensemble_agreement"]) == ["HIGH", "MEDIUM", "LOW", "NONE"]


def test_clean_vs_warned_grouping_works(tmp_path):
    input_dir = _write_input(tmp_path, [_row(warning=""), _row(warning="WARN_FLAG")])
    df = analysis.load_evaluation_rows(input_dir)

    assert list(df["warning_state"]) == ["clean", "warned"]


def test_creates_summary_csv_and_markdown(tmp_path):
    input_dir = _write_input(tmp_path, _rows(60, 45, subtype="UNDER_35"))
    output_dir = tmp_path / "out"

    table, markdown = analysis.run(input_dir=input_dir, output_dir=output_dir)

    assert not table.empty
    assert (output_dir / analysis.OUTPUT_CSV).exists()
    assert (output_dir / analysis.OUTPUT_MD).exists()
    assert "Phase 11 is diagnostic only. No tier rules were changed." in markdown
    assert "Phase 11 Recommendation" in markdown


def test_detects_promote_candidate_when_subgroup_beats_baseline():
    rows = _rows(50, 45, market_tier="A_TIER", subtype="UNDER_35")
    rows += _rows(50, 35, market_tier="A_TIER", subtype="UNDER_25")
    table = analysis.apply_candidate_detection(
        analysis.build_summary_table(pd.DataFrame(rows).assign(type_success_bool=lambda d: d["type_success"].astype(bool))),
        min_sample=50,
        small_sample=20,
        threshold_pp=3.0,
    )

    promote = table[
        (table["section_id"] == "E")
        & (table["recommended_market_subtype"] == "UNDER_35")
    ].iloc[0]
    assert promote["candidate_category"] == "PROMOTE_CANDIDATE"


def test_detects_downgrade_candidate_when_subgroup_trails_baseline():
    rows = _rows(50, 45, market_tier="A_TIER", subtype="UNDER_35")
    rows += _rows(50, 35, market_tier="A_TIER", subtype="UNDER_25")
    table = analysis.apply_candidate_detection(
        analysis.build_summary_table(pd.DataFrame(rows).assign(type_success_bool=lambda d: d["type_success"].astype(bool))),
        min_sample=50,
        small_sample=20,
        threshold_pp=3.0,
    )

    downgrade = table[
        (table["section_id"] == "E")
        & (table["recommended_market_subtype"] == "UNDER_25")
    ].iloc[0]
    assert downgrade["candidate_category"] == "DOWNGRADE_CANDIDATE"


def test_detects_no_go_candidate_below_65_percent():
    rows = _rows(50, 30, market_tier="DOWNGRADE", subtype="BTTS")
    rows += _rows(50, 45, market_tier="DOWNGRADE", subtype="UNDER_35")
    table = analysis.apply_candidate_detection(
        analysis.build_summary_table(pd.DataFrame(rows).assign(type_success_bool=lambda d: d["type_success"].astype(bool))),
        min_sample=50,
        small_sample=20,
        threshold_pp=3.0,
    )

    no_go = table[
        (table["section_id"] == "E")
        & (table["recommended_market_subtype"] == "BTTS")
    ].iloc[0]
    assert no_go["candidate_category"] == "NO_GO_CANDIDATE"


def test_marks_small_sample_observe():
    rows = _rows(19, 18, market_tier="A_TIER", subtype="SMALL")
    table = analysis.apply_candidate_detection(
        analysis.build_summary_table(pd.DataFrame(rows).assign(type_success_bool=lambda d: d["type_success"].astype(bool))),
        min_sample=50,
        small_sample=20,
        threshold_pp=3.0,
    )

    assert "SMALL_SAMPLE_OBSERVE" in set(table["candidate_category"])


def test_final_recommendation_section_present(tmp_path):
    input_dir = _write_input(tmp_path, _rows(60, 45, market_tier="A_TIER"))
    _, markdown = analysis.run(input_dir=input_dir, output_dir=tmp_path / "out")

    assert "## Phase 11 Recommendation" in markdown


def test_script_does_not_modify_market_tier_or_probability_logic(tmp_path):
    watched = [
        ROOT / "src/football_prediction_v19/diagnostics/market_tier.py",
        ROOT / "src/football_prediction_v19/model.py",
        ROOT / "scripts/run_season_replay_audit.py",
    ]
    before = {path: _hash(path) for path in watched}
    input_dir = _write_input(tmp_path, _rows(60, 45, market_tier="A_TIER"))

    analysis.run(input_dir=input_dir, output_dir=tmp_path / "out")

    after = {path: _hash(path) for path in watched}
    assert after == before
