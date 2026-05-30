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

import audit_phase11_3_impact as audit  # noqa: E402


PHASE_FLAG = "phase_11_3_downgrade_low_control_no_go"


def _row(
    *,
    success=True,
    league="League A",
    market_tier="HARD_NO_GO",
    market_type="BTTS_OVER",
    subtype="BTTS",
    reason="",
    flags="",
) -> dict:
    return {
        "type_success": "" if success is None else success,
        "league": league,
        "market_tier": market_tier,
        "recommended_market_type": market_type,
        "recommended_market_subtype": subtype,
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


def test_detects_phase11_3_impacted_rows_from_market_tier_reason(tmp_path):
    input_dir = _write_input(tmp_path, [
        _row(reason=f"base [{PHASE_FLAG}]"),
        _row(reason="base"),
    ])

    df = audit.load_evaluation_rows(input_dir)

    assert df["phase_11_3_impacted"].tolist() == [True, False]
    assert df["phase_11_3_flags"].iloc[0] == PHASE_FLAG


def test_computes_impacted_vs_non_impacted_rates(tmp_path):
    rows = _rows(10, 6, reason=PHASE_FLAG)
    rows += _rows(10, 8, market_tier="A_TIER", reason="")
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))

    summary = audit.build_executive_summary(df)

    assert summary["impacted_rows"] == 10
    assert summary["impacted_success_rate"] == 0.6
    assert summary["non_impacted_success_rate"] == 0.8


def test_groups_by_flag(tmp_path):
    other = "phase_11_3_downgrade_medium_fav_no_go"
    rows = _rows(3, 2, flags=PHASE_FLAG)
    rows += _rows(2, 1, flags=other)
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))

    table = audit.build_impact_by_flag(df)

    assert set(table["phase_11_3_flag"]) == {PHASE_FLAG, other}
    row = table[table["phase_11_3_flag"] == PHASE_FLAG].iloc[0]
    assert row["n"] == 3
    assert row["hits"] == 2


def test_groups_by_league(tmp_path):
    rows = _rows(5, 3, league="League A", reason=PHASE_FLAG)
    rows += _rows(5, 4, league="League A", market_tier="A_TIER", reason="")
    rows += _rows(4, 1, league="League B", reason=PHASE_FLAG)
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))

    table = audit.build_impact_by_league(df)

    league_a = table[table["league"] == "League A"].iloc[0]
    assert league_a["n"] == 10
    assert league_a["impacted_n"] == 5
    assert league_a["impacted_success_rate"] == 0.6


def test_defensive_integrity_passes_when_only_hard_no_go_rows_are_impacted(tmp_path):
    rows = _rows(10, 6, market_tier="HARD_NO_GO", reason=PHASE_FLAG)
    rows += _rows(10, 8, market_tier="A_TIER", reason="")
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))

    integrity = audit.build_defensive_integrity(df)

    assert integrity["no_impacted_a_tier_rows"] is True
    assert integrity["no_impacted_b_tier_rows"] is True
    assert integrity["all_impacted_rows_defensive_tier_only"] is True


def test_defensive_integrity_fails_when_a_tier_impacted_row_exists(tmp_path):
    df = audit.load_evaluation_rows(_write_input(tmp_path, [
        _row(market_tier="A_TIER", reason=PHASE_FLAG),
    ]))

    integrity = audit.build_defensive_integrity(df)

    assert integrity["no_impacted_a_tier_rows"] is False
    assert integrity["all_impacted_rows_defensive_tier_only"] is False


def test_detects_super_a_tier_presence(tmp_path):
    df = audit.load_evaluation_rows(_write_input(tmp_path, [
        _row(market_tier="SUPER_A_TIER", reason=""),
    ]))

    integrity = audit.build_defensive_integrity(df)

    assert integrity["no_super_a_tier_present"] is False
    assert integrity["super_a_tier_rows"] == 1


def test_detects_league_outlier_when_impacted_rate_high_with_enough_sample(tmp_path):
    rows = _rows(20, 14, league="League A", reason=PHASE_FLAG)
    rows += _rows(10, 4, league="League B", reason=PHASE_FLAG)
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))
    league_table = audit.build_impact_by_league(df)

    outliers = audit.build_league_outliers(
        league_table,
        min_outlier_sample=20,
        high_rate_threshold=70.0,
    )

    assert set(outliers["league"]) == {"League A"}
    assert "impacted_hit_rate_high" in outliers.iloc[0]["outlier_reason"]


def test_recommendation_keep_phase11_3_as_is_when_low_rate_and_no_outlier(tmp_path):
    rows = _rows(60, 36, reason=PHASE_FLAG)
    rows += _rows(60, 45, market_tier="A_TIER", reason="")
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))
    table, executive, integrity, outliers, recommendation = audit.build_summary_table(df)

    assert not table.empty
    assert executive["impacted_success_rate"] == 0.6
    assert integrity["no_impacted_a_tier_rows"] is True
    assert outliers.empty
    assert recommendation == "KEEP_PHASE_11_3_AS_IS"


def test_recommendation_investigate_rule_too_broad_when_overall_impacted_rate_high(tmp_path):
    rows = _rows(60, 42, league="League A", reason=PHASE_FLAG)
    df = audit.load_evaluation_rows(_write_input(tmp_path, rows))

    _, _, _, _, recommendation = audit.build_summary_table(df)

    assert recommendation == "INVESTIGATE_RULE_TOO_BROAD"


def test_writes_csv_and_markdown(tmp_path):
    input_dir = _write_input(tmp_path, _rows(60, 36, reason=PHASE_FLAG))
    output_dir = tmp_path / "diagnostics"

    table, markdown = audit.run(input_dir=input_dir, output_dir=output_dir)

    assert not table.empty
    assert (output_dir / audit.OUTPUT_CSV).exists()
    assert (output_dir / audit.OUTPUT_MD).exists()
    assert "Phase 11.4 is diagnostic only. No tier rules were changed." in markdown
    assert "Phase 11.4 Recommendation" in markdown


def test_script_does_not_modify_protected_logic_files(tmp_path):
    protected = [
        ROOT / "src/football_prediction_v19/diagnostics/market_tier.py",
        ROOT / "src/football_prediction_v19/diagnostics/recommended_market.py",
        ROOT / "src/football_prediction_v19/model.py",
    ]
    before = {path: _hash(path) for path in protected}

    input_dir = _write_input(tmp_path, _rows(60, 36, reason=PHASE_FLAG))
    audit.run(input_dir=input_dir, output_dir=tmp_path / "diagnostics")

    after = {path: _hash(path) for path in protected}
    assert after == before
