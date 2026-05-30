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

import audit_hard_no_go_source_attribution as audit  # noqa: E402


PHASE_FLAG = "phase_11_3_downgrade_low_control_no_go"


def _row(
    *,
    success=True,
    league="Ligue 1",
    market_tier="HARD_NO_GO",
    subtype="BTTS",
    strength="LOW",
    warning="",
    reason="",
    flags="",
    odds_bucket="medium_fav (2.0-2.5)",
    ctrl_bucket="low (3-5)",
    season_phase="late",
) -> dict:
    return {
        "type_success": "" if success is None else success,
        "league": league,
        "market_tier": market_tier,
        "recommended_market_type": "BTTS_OVER",
        "recommended_market_subtype": subtype,
        "league_adjusted_strength": strength,
        "league_warning_flags": warning,
        "market_tier_reason": reason,
        "market_tier_flags": flags,
        "odds_bucket": odds_bucket,
        "ctrl_bucket": ctrl_bucket,
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


def test_filters_hard_no_go_rows_correctly(tmp_path):
    rows = [_row(market_tier="HARD_NO_GO"), _row(market_tier="A_TIER")]
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))

    hng = audit.hard_no_go_rows(df)

    assert len(hng) == 1
    assert hng.iloc[0]["market_tier"] == "HARD_NO_GO"


def test_parses_type_success_correctly():
    assert audit.parse_bool_success(True) is True
    assert audit.parse_bool_success("1") is True
    assert audit.parse_bool_success("yes") is True
    assert audit.parse_bool_success(False) is False
    assert audit.parse_bool_success("0") is False
    assert audit.parse_bool_success("no") is False
    assert audit.parse_bool_success("") is None


def test_classifies_both_over25_btts_permanent_hard_no_go():
    row = pd.Series(_row(subtype="BOTH_OVER25_BTTS", reason="permanent HARD_NO_GO"))

    assert "BOTH_OVER25_BTTS_PERMANENT_HARD_NO_GO" in audit.classify_hard_no_go_sources(row)


def test_classifies_suppressed_with_warning():
    row = pd.Series(_row(strength="SUPPRESSED", warning="active warning"))

    assert "SUPPRESSED_WITH_WARNING" in audit.classify_hard_no_go_sources(row)


def test_classifies_phase11_3_defensive_flags():
    row = pd.Series(_row(flags=PHASE_FLAG))

    assert "PHASE_11_3_DEFENSIVE_FLAG" in audit.classify_hard_no_go_sources(row)


def test_supports_multiple_source_categories_per_row():
    row = pd.Series(_row(
        subtype="BOTH_OVER25_BTTS",
        flags=PHASE_FLAG,
        reason="phase_11_3_hard_no_go_medium_fav_confirmed",
    ))

    sources = audit.classify_hard_no_go_sources(row)

    assert "PHASE_11_3_DEFENSIVE_FLAG" in sources
    assert "BOTH_OVER25_BTTS_PERMANENT_HARD_NO_GO" in sources
    assert "MEDIUM_FAV_CONFIRMATION" in sources


def test_computes_overall_source_attribution_rates(tmp_path):
    rows = _rows(10, 7, subtype="BOTH_OVER25_BTTS")
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))
    hng = audit.hard_no_go_rows(df)

    overall = audit.build_source_overall(hng)

    row = overall[overall["source_category"] == "BOTH_OVER25_BTTS_PERMANENT_HARD_NO_GO"].iloc[0]
    assert row["n"] == 10
    assert row["hits"] == 7
    assert row["success_rate"] == 0.7


def test_computes_ligue1_vs_other_league_source_comparison(tmp_path):
    rows = _rows(10, 7, league="Ligue 1", subtype="BOTH_OVER25_BTTS")
    rows += _rows(10, 4, league="Serie A", subtype="BOTH_OVER25_BTTS")
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))
    hng = audit.hard_no_go_rows(df)

    comp = audit.build_focus_vs_other_comparison(hng, "Ligue 1")

    row = comp[comp["source_category"] == "BOTH_OVER25_BTTS_PERMANENT_HARD_NO_GO"].iloc[0]
    assert row["ligue1_n"] == 10
    assert row["ligue1_rate"] == 0.7
    assert row["other_rate"] == 0.4
    assert row["delta_pp"] == 30.0


def test_flags_ligue1_source_too_strict_candidate(tmp_path):
    rows = _rows(20, 14, league="Ligue 1", subtype="BOTH_OVER25_BTTS")
    rows += _rows(20, 10, league="Serie A", subtype="BOTH_OVER25_BTTS")
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))
    hng = audit.hard_no_go_rows(df)
    comp = audit.build_focus_vs_other_comparison(hng, "Ligue 1")
    overall = audit.build_source_overall(hng)

    candidates = audit.build_candidate_sources(
        comp,
        overall,
        min_sample=20,
        global_min_sample=50,
        high_rate_threshold=70.0,
        delta_threshold_pp=5.0,
    )

    assert "LIGUE1_SOURCE_TOO_STRICT" in set(candidates["candidate_label"])


def test_real_style_comparison_creates_ligue1_source_too_strict_candidates():
    comparison = pd.DataFrame([
        {
            "source_category": "BOTH_OVER25_BTTS_PERMANENT_HARD_NO_GO",
            "ligue1_n": 45,
            "ligue1_rate": 0.778,
            "other_n": 245,
            "other_rate": 0.685,
            "delta_pp": 9.31,
        },
        {
            "source_category": "SUPPRESSED_WITH_WARNING",
            "ligue1_n": 57,
            "ligue1_rate": 0.719,
            "other_n": 225,
            "other_rate": 0.662,
            "delta_pp": 5.72,
        },
        {
            "source_category": "LEAGUE_PROFILE_SUPPRESSION",
            "ligue1_n": 45,
            "ligue1_rate": 0.778,
            "other_n": 217,
            "other_rate": 0.691,
            "delta_pp": 8.67,
        },
    ])
    overall = pd.DataFrame(columns=["source_category", "n", "success_rate"])

    candidates = audit.build_candidate_sources(
        comparison,
        overall,
        min_sample=20,
        global_min_sample=50,
        high_rate_threshold=70.0,
        delta_threshold_pp=5.0,
    )

    ligue_sources = set(candidates[
        candidates["candidate_label"] == "LIGUE1_SOURCE_TOO_STRICT"
    ]["source_category"])
    assert ligue_sources == {
        "BOTH_OVER25_BTTS_PERMANENT_HARD_NO_GO",
        "SUPPRESSED_WITH_WARNING",
        "LEAGUE_PROFILE_SUPPRESSION",
    }


def test_flags_global_source_too_strict_candidate(tmp_path):
    rows = _rows(60, 42, league="Ligue 1", subtype="BOTH_OVER25_BTTS")
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))
    hng = audit.hard_no_go_rows(df)
    comp = audit.build_focus_vs_other_comparison(hng, "Ligue 1")
    overall = audit.build_source_overall(hng)

    candidates = audit.build_candidate_sources(
        comp,
        overall,
        min_sample=20,
        global_min_sample=50,
        high_rate_threshold=70.0,
        delta_threshold_pp=5.0,
    )

    assert "GLOBAL_SOURCE_TOO_STRICT" in set(candidates["candidate_label"])


def test_global_candidate_does_not_suppress_ligue1_candidate():
    comparison = pd.DataFrame([{
        "source_category": "LEAGUE_PROFILE_SUPPRESSION",
        "ligue1_n": 45,
        "ligue1_rate": 0.778,
        "other_n": 217,
        "other_rate": 0.691,
        "delta_pp": 8.67,
    }])
    overall = pd.DataFrame([{
        "source_category": "LEAGUE_PROFILE_SUPPRESSION",
        "n": 262,
        "success_rate": 0.706,
    }])

    candidates = audit.build_candidate_sources(
        comparison,
        overall,
        min_sample=20,
        global_min_sample=50,
        high_rate_threshold=70.0,
        delta_threshold_pp=5.0,
    )

    labels = set(candidates["candidate_label"])
    assert "LIGUE1_SOURCE_TOO_STRICT" in labels
    assert "GLOBAL_SOURCE_TOO_STRICT" in labels
    assert set(candidates["section"]) == {"candidate_source_problems"}


def test_section_e_comparison_rows_are_unique_per_source_category(tmp_path):
    rows = _rows(10, 8, league="Ligue 1", subtype="BOTH_OVER25_BTTS", flags=PHASE_FLAG)
    rows += _rows(10, 6, league="Serie A", subtype="BOTH_OVER25_BTTS", flags=PHASE_FLAG)
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))
    hng = audit.hard_no_go_rows(df)

    comparison = audit.build_focus_vs_other_comparison(hng, "Ligue 1")

    assert comparison["source_category"].is_unique


def test_recommendation_is_consistent_with_ligue1_candidate_label():
    executive = {
        "total_hard_no_go_rows": 120,
        "ligue1_hard_no_go_rows": 60,
        "source_attribution_coverage": 1.0,
    }
    candidates = pd.DataFrame([
        {"candidate_label": "GLOBAL_SOURCE_TOO_STRICT", "source_category": "LEAGUE_PROFILE_SUPPRESSION"},
        {"candidate_label": "LIGUE1_SOURCE_TOO_STRICT", "source_category": "SUPPRESSED_WITH_WARNING"},
    ])

    recommendation = audit.phase11_6_recommendation(executive, candidates, min_sample=20)

    assert recommendation == "INVESTIGATE_LIGUE1_SOURCE_RELAXATION"


def test_flags_unknown_source_review_candidate(tmp_path):
    rows = _rows(20, 10, league="Ligue 1", subtype="MYSTERY", reason="")
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))
    hng = audit.hard_no_go_rows(df)
    comp = audit.build_focus_vs_other_comparison(hng, "Ligue 1")
    overall = audit.build_source_overall(hng)

    candidates = audit.build_candidate_sources(
        comp,
        overall,
        min_sample=20,
        global_min_sample=50,
        high_rate_threshold=70.0,
        delta_threshold_pp=5.0,
    )

    assert "UNKNOWN_SOURCE_REVIEW" in set(candidates["candidate_label"])


def test_returns_keep_current_sources_when_no_candidates_and_coverage_high(tmp_path):
    rows = _rows(60, 36, league="Ligue 1", subtype="BOTH_OVER25_BTTS")
    rows += _rows(60, 36, league="Serie A", subtype="BOTH_OVER25_BTTS")
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))

    _, _, recommendation = audit.build_summary_table(df)

    assert recommendation == "KEEP_CURRENT_HARD_NO_GO_SOURCES"


def test_returns_inconclusive_when_sample_too_small(tmp_path):
    rows = _rows(40, 30, league="Ligue 1", subtype="BOTH_OVER25_BTTS")
    rows += _rows(40, 20, league="Serie A", subtype="BOTH_OVER25_BTTS")
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))

    _, _, recommendation = audit.build_summary_table(df)

    assert recommendation == "INCONCLUSIVE_MORE_REPLAY_REQUIRED"


def test_writes_csv_and_markdown(tmp_path):
    rows = _rows(60, 36, league="Ligue 1", subtype="BOTH_OVER25_BTTS")
    rows += _rows(60, 36, league="Serie A", subtype="BOTH_OVER25_BTTS")
    input_dir = _write_input(tmp_path, rows)
    output_dir = tmp_path / "diagnostics"

    table, markdown = audit.run(input_dir=input_dir, output_dir=output_dir)

    assert not table.empty
    assert (output_dir / audit.OUTPUT_CSV).exists()
    assert (output_dir / audit.OUTPUT_MD).exists()
    assert "Phase 11.6 is diagnostic only. No tier rules were changed." in markdown
    assert "Phase 11.6 Recommendation" in markdown


def test_script_does_not_modify_protected_logic_files(tmp_path):
    protected = [
        ROOT / "src/football_prediction_v19/diagnostics/market_tier.py",
        ROOT / "src/football_prediction_v19/diagnostics/recommended_market.py",
        ROOT / "src/football_prediction_v19/model.py",
    ]
    before = {path: _hash(path) for path in protected}

    rows = _rows(60, 36, league="Ligue 1", subtype="BOTH_OVER25_BTTS")
    rows += _rows(60, 36, league="Serie A", subtype="BOTH_OVER25_BTTS")
    audit.run(input_dir=_write_input(tmp_path, rows), output_dir=tmp_path / "diagnostics")

    after = {path: _hash(path) for path in protected}
    assert after == before
