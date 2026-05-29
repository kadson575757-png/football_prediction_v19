# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import sys
import warnings
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


def test_unknown_market_tier_rows_excluded_from_default_decision_scope(tmp_path):
    rows = _rows(50, 50, market_tier="UNKNOWN", strength="HIGH")
    rows += _rows(50, 25, market_tier="UNKNOWN", strength="LOW")
    input_dir = _write_input(tmp_path, rows)

    table, markdown = analysis.run(input_dir=input_dir, output_dir=tmp_path / "out")

    assert table.empty
    assert "Decision scope used: modern-tier" in markdown
    assert "UNKNOWN market_tier rows: 100" in markdown
    assert "HOLD_CURRENT_RULES" in markdown or "INCONCLUSIVE" in markdown


def test_scope_all_includes_unknown_rows(tmp_path):
    rows = _rows(50, 50, market_tier="UNKNOWN", strength="HIGH")
    rows += _rows(50, 25, market_tier="UNKNOWN", strength="LOW")
    input_dir = _write_input(tmp_path, rows)

    table, markdown = analysis.run(input_dir=input_dir, output_dir=tmp_path / "out", scope="all")

    assert "UNKNOWN" in set(table.get("market_tier", pd.Series(dtype=str)).dropna().astype(str))
    assert "Decision scope used: all" in markdown


def test_scope_ensemble_only_uses_high_medium_low_rows(tmp_path):
    rows = _rows(10, 8, market_tier="A_TIER", ensemble_agreement="HIGH")
    rows += _rows(10, 7, market_tier="A_TIER", ensemble_agreement="MEDIUM")
    rows += _rows(50, 0, market_tier="A_TIER", ensemble_agreement="NONE")
    input_dir = _write_input(tmp_path, rows)

    table, markdown = analysis.run(input_dir=input_dir, output_dir=tmp_path / "out", scope="ensemble-only")

    section_b = table[table["section_id"] == "B"]
    assert set(section_b["ensemble_agreement"]) == {"HIGH", "MEDIUM"}
    assert "Decision scope used: ensemble-only" in markdown


def test_markdown_states_decision_scope(tmp_path):
    input_dir = _write_input(tmp_path, _rows(25, 20, market_tier="A_TIER"))

    _, markdown = analysis.run(input_dir=input_dir, output_dir=tmp_path / "out", scope="modern-tier")

    assert "Decision scope used: modern-tier" in markdown


def test_futurewarning_no_longer_appears(tmp_path):
    input_dir = _write_input(tmp_path, _rows(10, 8, market_tier="A_TIER"))

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        analysis.run(input_dir=input_dir, output_dir=tmp_path / "out")

    assert not any(item.category is FutureWarning for item in caught)


def test_candidate_decision_changes_when_unknown_rows_are_excluded(tmp_path):
    modern_rows = _rows(60, 45, market_tier="A_TIER", strength="HIGH")
    modern_rows += _rows(60, 45, market_tier="A_TIER", strength="LOW")
    unknown_rows = _rows(50, 50, market_tier="UNKNOWN", strength="HIGH")
    unknown_rows += _rows(50, 25, market_tier="UNKNOWN", strength="LOW")
    input_dir = _write_input(tmp_path, modern_rows + unknown_rows)

    modern_table, modern_md = analysis.run(
        input_dir=input_dir,
        output_dir=tmp_path / "modern",
        scope="modern-tier",
    )
    all_table, all_md = analysis.run(
        input_dir=input_dir,
        output_dir=tmp_path / "all",
        scope="all",
    )

    assert analysis.phase11_recommendation(modern_table) == "HOLD_CURRENT_RULES"
    assert analysis.phase11_recommendation(all_table) != "HOLD_CURRENT_RULES"
    assert "Decision scope used: modern-tier" in modern_md
    assert "Decision scope used: all" in all_md


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
