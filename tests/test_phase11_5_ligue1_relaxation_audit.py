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

import audit_ligue1_defensive_relaxation as audit  # noqa: E402


PHASE_FLAG = "phase_11_3_downgrade_low_control_no_go"


def _row(
    *,
    success=True,
    league="Ligue 1",
    market_tier="HARD_NO_GO",
    market_type="BTTS_OVER",
    subtype="BTTS",
    strength="LOW",
    warning="",
    ctrl_bucket="low (3-5)",
    chaos_bucket="medium",
    odds_bucket="medium_fav (2.0-2.5)",
    season_phase="mid",
    ensemble_agreement="NONE",
    reason="",
    flags="",
) -> dict:
    return {
        "type_success": "" if success is None else success,
        "league": league,
        "market_tier": market_tier,
        "recommended_market_type": market_type,
        "recommended_market_subtype": subtype,
        "league_adjusted_strength": strength,
        "league_warning_flags": warning,
        "ctrl_bucket": ctrl_bucket,
        "chaos_bucket": chaos_bucket,
        "odds_bucket": odds_bucket,
        "season_phase": season_phase,
        "ensemble_agreement": ensemble_agreement,
        "market_tier_reason": reason,
        "market_tier_flags": flags,
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


def test_filters_ligue1_rows_correctly(tmp_path):
    rows = [_row(league="Ligue 1"), _row(league="Serie A")]
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))
    focus, other = audit.split_focus(df, "Ligue 1")

    assert len(focus) == 1
    assert len(other) == 1
    assert focus.iloc[0]["league"] == "Ligue 1"


def test_parses_type_success_correctly():
    assert audit.parse_bool_success(True) is True
    assert audit.parse_bool_success("1") is True
    assert audit.parse_bool_success("yes") is True
    assert audit.parse_bool_success(False) is False
    assert audit.parse_bool_success("0") is False
    assert audit.parse_bool_success("no") is False
    assert audit.parse_bool_success("") is None


def test_detects_phase11_3_flags(tmp_path):
    df = audit.load_evaluation_rows(_write_input(tmp_path, [
        _row(reason=f"base [{PHASE_FLAG}]"),
        _row(reason="base"),
    ]))

    assert df["phase_11_3_impacted"].tolist() == [True, False]
    assert df["phase_11_3_flag"].iloc[0] == PHASE_FLAG


def test_computes_ligue1_hard_no_go_rate(tmp_path):
    rows = _rows(10, 7, league="Ligue 1", market_tier="HARD_NO_GO")
    rows += _rows(10, 8, league="Ligue 1", market_tier="A_TIER")
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))

    summary = audit.build_executive_summary(df, "Ligue 1")

    assert summary["ligue1_hard_no_go_rows"] == 10
    assert summary["ligue1_hard_no_go_success_rate"] == 0.7


def test_computes_non_ligue1_comparison_rate(tmp_path):
    rows = _rows(10, 7, league="Ligue 1", reason=PHASE_FLAG)
    rows += _rows(10, 4, league="Serie A", reason=PHASE_FLAG)
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))

    summary = audit.build_executive_summary(df, "Ligue 1")

    assert summary["ligue1_impacted_success_rate"] == 0.7
    assert summary["non_ligue1_impacted_success_rate"] == 0.4
    assert summary["gap_vs_non_ligue1_pp"] == 30.0


def test_detects_flag_relaxation_candidate(tmp_path):
    rows = _rows(20, 14, league="Ligue 1", reason=PHASE_FLAG)
    rows += _rows(20, 10, league="Serie A", reason=PHASE_FLAG)
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))
    comparison = audit.build_comparison(df, "Ligue 1")

    candidates = audit.build_candidate_zones(
        comparison,
        min_sample=20,
        high_rate_threshold=70.0,
        delta_threshold_pp=5.0,
    )

    assert "LIGUE1_RELAX_PHASE_11_3_FLAG" in set(candidates["candidate_category"])


def test_detects_subtype_relaxation_candidate(tmp_path):
    rows = _rows(20, 14, league="Ligue 1", subtype="BTTS")
    rows += _rows(20, 10, league="Serie A", subtype="BTTS")
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))
    comparison = audit.build_comparison(df, "Ligue 1")

    candidates = audit.build_candidate_zones(
        comparison,
        min_sample=20,
        high_rate_threshold=70.0,
        delta_threshold_pp=5.0,
    )

    assert "LIGUE1_RELAX_SUBTYPE" in set(candidates["candidate_category"])


def test_returns_keep_phase11_3_as_is_when_no_candidate_exists(tmp_path):
    rows = _rows(20, 12, league="Ligue 1", reason=PHASE_FLAG)
    rows += _rows(20, 12, league="Serie A", reason=PHASE_FLAG)
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))

    _, _, recommendation = audit.build_summary_table(df)

    assert recommendation == "KEEP_PHASE_11_3_AS_IS"


def test_returns_profile_review_when_overall_hard_no_go_high_without_single_candidate(tmp_path):
    rows = []
    for subtype in ("A", "B", "C", "D"):
        rows += _rows(5, 3, league="Ligue 1", subtype=subtype, reason=PHASE_FLAG)
        rows += _rows(5, 4, league="Ligue 1", subtype=subtype, reason="")
    rows += _rows(40, 20, league="Serie A", subtype="A", reason=PHASE_FLAG)
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))

    _, _, recommendation = audit.build_summary_table(df)

    assert recommendation == "INVESTIGATE_LIGUE1_PROFILE_REVIEW"


def test_returns_inconclusive_when_impacted_rows_below_min_sample(tmp_path):
    rows = _rows(19, 15, league="Ligue 1", reason=PHASE_FLAG)
    rows += _rows(20, 10, league="Serie A", reason=PHASE_FLAG)
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))

    _, _, recommendation = audit.build_summary_table(df)

    assert recommendation == "INCONCLUSIVE_MORE_REPLAY_REQUIRED"


def test_writes_csv_and_markdown(tmp_path):
    input_dir = _write_input(tmp_path, _rows(20, 12, reason=PHASE_FLAG))
    output_dir = tmp_path / "diagnostics"

    table, markdown = audit.run(input_dir=input_dir, output_dir=output_dir)

    assert not table.empty
    assert (output_dir / audit.OUTPUT_CSV).exists()
    assert (output_dir / audit.OUTPUT_MD).exists()
    assert "Phase 11.5 is diagnostic only. No tier rules were changed." in markdown
    assert "Phase 11.5 Recommendation" in markdown


def test_script_does_not_modify_protected_logic_files(tmp_path):
    protected = [
        ROOT / "src/football_prediction_v19/diagnostics/market_tier.py",
        ROOT / "src/football_prediction_v19/diagnostics/recommended_market.py",
        ROOT / "src/football_prediction_v19/model.py",
    ]
    before = {path: _hash(path) for path in protected}

    input_dir = _write_input(tmp_path, _rows(20, 12, reason=PHASE_FLAG))
    audit.run(input_dir=input_dir, output_dir=tmp_path / "diagnostics")

    after = {path: _hash(path) for path in protected}
    assert after == before
