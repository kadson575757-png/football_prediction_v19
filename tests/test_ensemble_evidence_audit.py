# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import aggregate_ensemble_evidence as audit  # noqa: E402


def _row(
    *,
    league: str = "League A",
    market_tier: str = "A_TIER",
    agreement: str = "HIGH",
    success: bool | None = True,
    subtype: str = "UNDER_35",
    warning: str = "",
) -> dict:
    return {
        "league": league,
        "market_tier": market_tier,
        "ensemble_agreement": agreement,
        "type_success": "" if success is None else success,
        "recommended_market_subtype": subtype,
        "league_warning_flags": warning,
    }


def _write_eval(tmp_path: Path, rows: list[dict]) -> Path:
    input_dir = tmp_path / "season_replay"
    input_dir.mkdir()
    pd.DataFrame(rows).to_csv(input_dir / "synthetic_evaluation.csv", index=False)
    return input_dir


def _rows(n: int, hits: int, **kwargs) -> list[dict]:
    return [
        _row(success=i < hits, **kwargs)
        for i in range(n)
    ]


def test_aggregates_market_tier_x_ensemble_agreement_correctly(tmp_path):
    input_dir = _write_eval(
        tmp_path,
        _rows(3, 2, market_tier="A_TIER", agreement="HIGH")
        + _rows(2, 1, market_tier="A_TIER", agreement="MEDIUM")
        + _rows(4, 3, market_tier="B_TIER", agreement="HIGH"),
    )
    df = audit.load_evaluation_rows(input_dir)
    table = audit.build_summary_table(df)

    section = table[table["section"] == "success_by_market_tier_x_ensemble_agreement"]
    row = section[
        (section["market_tier"] == "A_TIER")
        & (section["ensemble_agreement"] == "HIGH")
    ].iloc[0]
    assert int(row["n"]) == 3
    assert int(row["hits"]) == 2
    assert float(row["success_rate"]) == 0.6667


def test_excludes_blank_type_success_rows(tmp_path):
    input_dir = _write_eval(
        tmp_path,
        [_row(success=True), _row(success=False), _row(success=None)],
    )
    df = audit.load_evaluation_rows(input_dir)

    assert len(df) == 2


def test_flags_small_sample_n_under_20(tmp_path):
    input_dir = _write_eval(tmp_path, _rows(19, 10, agreement="HIGH"))
    table = audit.build_summary_table(audit.load_evaluation_rows(input_dir))

    row = table[
        (table["section"] == "success_by_ensemble_agreement")
        & (table["ensemble_agreement"] == "HIGH")
    ].iloc[0]
    assert bool(row["small_sample"]) is True


def test_super_a_decision_yes_when_high_clearly_beats_medium_with_samples():
    rows = []
    for league in ("League A", "League B", "League C"):
        rows += _rows(20, 16, league=league, market_tier="A_TIER", agreement="HIGH")
        rows += _rows(20, 12, league=league, market_tier="A_TIER", agreement="MEDIUM")
    df = pd.DataFrame(rows)
    df["type_success_bool"] = df["type_success"].astype(bool)

    decision, reasons = audit.super_a_tier_decision(df)

    assert decision == "YES"
    assert any("stable" in reason for reason in reasons)


def test_decision_ignores_none_rows():
    rows = []
    for league in ("League A", "League B", "League C"):
        rows += _rows(20, 16, league=league, market_tier="A_TIER", agreement="HIGH")
        rows += _rows(20, 12, league=league, market_tier="A_TIER", agreement="MEDIUM")
    rows += _rows(500, 0, league="Old League", market_tier="A_TIER", agreement="NONE")
    df = pd.DataFrame(rows)
    df["type_success_bool"] = df["type_success"].astype(bool)

    decision, reasons = audit.super_a_tier_decision(df)

    assert decision == "YES"
    assert any("Decision is based on ensemble-only rows." in reason for reason in reasons)


def test_decision_ignores_blank_market_tier_rows():
    rows = []
    for league in ("League A", "League B", "League C"):
        rows += _rows(20, 16, league=league, market_tier="A_TIER", agreement="HIGH")
        rows += _rows(20, 12, league=league, market_tier="A_TIER", agreement="MEDIUM")
    rows += _rows(500, 0, league="Old League", market_tier="", agreement="HIGH")
    df = pd.DataFrame(rows)
    df["type_success_bool"] = df["type_success"].astype(bool)

    decision, _ = audit.super_a_tier_decision(df)

    assert decision == "YES"


def test_high_vs_medium_decision_uses_ensemble_only_rows():
    rows = []
    for league in ("League A", "League B", "League C"):
        rows += _rows(20, 12, league=league, market_tier="A_TIER", agreement="HIGH")
        rows += _rows(20, 16, league=league, market_tier="A_TIER", agreement="MEDIUM")
    rows += _rows(500, 500, league="Old League", market_tier="A_TIER", agreement="NONE")
    df = pd.DataFrame(rows)
    df["type_success_bool"] = df["type_success"].astype(bool)

    decision, reasons = audit.super_a_tier_decision(df)

    assert decision == "NO"
    assert any("worse than or equal" in reason for reason in reasons)


def test_super_a_decision_no_when_high_does_not_beat_medium():
    rows = []
    for league in ("League A", "League B", "League C"):
        rows += _rows(20, 12, league=league, market_tier="A_TIER", agreement="HIGH")
        rows += _rows(20, 14, league=league, market_tier="A_TIER", agreement="MEDIUM")
    df = pd.DataFrame(rows)
    df["type_success_bool"] = df["type_success"].astype(bool)

    decision, reasons = audit.super_a_tier_decision(df)

    assert decision == "NO"
    assert any("worse than or equal" in reason for reason in reasons)


def test_super_a_decision_inconclusive_when_sample_too_small():
    rows = _rows(10, 9, market_tier="A_TIER", agreement="HIGH")
    rows += _rows(10, 6, market_tier="A_TIER", agreement="MEDIUM")
    df = pd.DataFrame(rows)
    df["type_success_bool"] = df["type_success"].astype(bool)

    decision, reasons = audit.super_a_tier_decision(df)

    assert decision == "INCONCLUSIVE"
    assert any("too small" in reason for reason in reasons)


def test_writes_both_csv_and_markdown_outputs(tmp_path):
    input_dir = _write_eval(
        tmp_path,
        _rows(25, 20, market_tier="A_TIER", agreement="HIGH", warning="")
        + _rows(25, 18, market_tier="A_TIER", agreement="MEDIUM", warning="warn"),
    )
    output_dir = tmp_path / "out"

    table, markdown = audit.run(input_dir, output_dir)

    assert not table.empty
    assert (output_dir / audit.OUTPUT_CSV).exists()
    assert (output_dir / audit.OUTPUT_MD).exists()
    assert "SUPER_A_TIER should not be activated unless HIGH ensemble consensus shows a stable uplift." in markdown
    assert "SUPER_A_TIER Evidence Decision" in markdown


def test_markdown_includes_old_non_ensemble_warning(tmp_path):
    input_dir = _write_eval(
        tmp_path,
        _rows(25, 20, market_tier="A_TIER", agreement="HIGH")
        + _rows(25, 18, market_tier="A_TIER", agreement="MEDIUM")
        + _rows(5, 3, market_tier="", agreement="NONE"),
    )

    _, markdown = audit.run(input_dir, tmp_path / "out")

    assert "Total evaluatable rows:" in markdown
    assert "Ensemble evaluatable rows:" in markdown
    assert "Non-ensemble/NONE rows:" in markdown
    assert "Blank market_tier rows:" in markdown
    assert "WARNING: old/non-ensemble rows or blank market_tier rows are present" in markdown
    assert "Decision is based on ensemble-only rows." in markdown


def test_csv_still_writes_all_requested_summary_sections(tmp_path):
    input_dir = _write_eval(
        tmp_path,
        _rows(25, 20, market_tier="A_TIER", agreement="HIGH", subtype="UNDER_35")
        + _rows(25, 18, market_tier="A_TIER", agreement="MEDIUM", subtype="UNDER_25")
        + _rows(25, 15, market_tier="B_TIER", agreement="LOW", subtype="BTTS", warning="warn"),
    )
    table, _ = audit.run(input_dir, tmp_path / "out")

    assert {
        "success_by_ensemble_agreement",
        "success_by_market_tier",
        "success_by_market_tier_x_ensemble_agreement",
        "success_by_league_x_market_tier_x_ensemble_agreement",
        "success_by_recommended_market_subtype_x_ensemble_agreement",
        "success_by_league_warning_flags_clean_vs_warned",
    } <= set(table["section"])


def test_yes_decision_requires_required_threshold():
    rows = []
    for league in ("League A", "League B", "League C"):
        rows += _rows(20, 13, league=league, market_tier="A_TIER", agreement="HIGH")
        rows += _rows(20, 13, league=league, market_tier="A_TIER", agreement="MEDIUM")
    df = pd.DataFrame(rows)
    df["type_success_bool"] = df["type_success"].astype(bool)

    decision, _ = audit.super_a_tier_decision(df)

    assert decision == "NO"
