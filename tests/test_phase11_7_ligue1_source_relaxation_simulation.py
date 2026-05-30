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

import simulate_ligue1_source_relaxation as sim  # noqa: E402


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
    chaos_bucket="medium",
    season_phase="late",
    market_type="BTTS_OVER",
) -> dict:
    return {
        "type_success": "" if success is None else success,
        "league": league,
        "market_tier": market_tier,
        "recommended_market_type": market_type,
        "recommended_market_subtype": subtype,
        "league_adjusted_strength": strength,
        "league_warning_flags": warning,
        "market_tier_reason": reason,
        "market_tier_flags": flags,
        "odds_bucket": odds_bucket,
        "ctrl_bucket": ctrl_bucket,
        "chaos_bucket": chaos_bucket,
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


def _base_rows() -> list[dict]:
    rows = []
    rows += _rows(20, 18, subtype="BOTH_OVER25_BTTS")
    rows += _rows(20, 18, strength="SUPPRESSED", warning="active warning", subtype="BTTS")
    rows += _rows(20, 18, flags="SUBTYPE_SUPPRESSED", subtype="OVER_25")
    rows += _rows(20, 0, subtype="LIGUE1_DIRECTION")
    rows += _rows(20, 18, market_tier="A_TIER", subtype="UNDER_35", market_type="UNDER")
    rows += _rows(20, 17, market_tier="B_TIER", subtype="DOUBLE_CHANCE_1X", market_type="DOUBLE_CHANCE")
    rows += _rows(10, 5, market_tier="DOWNGRADE", subtype="BTTS")
    rows += _rows(10, 8, league="Serie A", subtype="BOTH_OVER25_BTTS")
    return rows


def test_filters_ligue1_hard_no_go_rows_correctly(tmp_path):
    df = sim.load_evaluation_rows(_write_input(tmp_path, _base_rows()))
    hng = sim.ligue1_hard_no_go_rows(df)

    assert len(hng) == 80
    assert set(hng["league"]) == {"Ligue 1"}
    assert set(hng["market_tier"]) == {"HARD_NO_GO"}


def test_parses_type_success_correctly():
    assert sim.parse_bool_success(True) is True
    assert sim.parse_bool_success("1") is True
    assert sim.parse_bool_success("yes") is True
    assert sim.parse_bool_success(False) is False
    assert sim.parse_bool_success("0") is False
    assert sim.parse_bool_success("no") is False
    assert sim.parse_bool_success("") is None


def test_classifies_source_categories_using_shared_attribution_logic(tmp_path):
    df = sim.load_evaluation_rows(_write_input(tmp_path, [
        _row(subtype="BOTH_OVER25_BTTS"),
        _row(strength="SUPPRESSED", warning="active warning"),
        _row(flags="SUBTYPE_SUPPRESSED"),
        _row(flags=PHASE_FLAG),
    ]))

    categories = set(" | ".join(df["source_categories"]).split(" | "))

    assert "BOTH_OVER25_BTTS_PERMANENT_HARD_NO_GO" in categories
    assert "SUPPRESSED_WITH_WARNING" in categories
    assert "LEAGUE_PROFILE_SUPPRESSION" in categories
    assert "PHASE_11_3_DEFENSIVE_FLAG" in categories


def test_simulates_relax_both_over25_btts_without_modifying_original_rows(tmp_path):
    df = sim.load_evaluation_rows(_write_input(tmp_path, _base_rows()))
    before = df["market_tier"].copy(deep=True)

    simulated, relaxed = sim.simulate_variant(
        df, "relax_both_over25_btts", {"BOTH_OVER25_BTTS_PERMANENT_HARD_NO_GO"}, "Ligue 1"
    )

    assert len(relaxed) == 20
    assert (simulated.loc[relaxed.index, "simulated_market_tier"] == "DOWNGRADE").all()
    assert df["market_tier"].equals(before)


def test_simulates_relax_suppressed_with_warning_without_modifying_original_rows(tmp_path):
    df = sim.load_evaluation_rows(_write_input(tmp_path, _base_rows()))
    before = df["market_tier"].copy(deep=True)

    _, relaxed = sim.simulate_variant(
        df, "relax_suppressed_with_warning", {"SUPPRESSED_WITH_WARNING"}, "Ligue 1"
    )

    assert len(relaxed) == 20
    assert df["market_tier"].equals(before)


def test_simulates_relax_league_profile_suppression_without_modifying_original_rows(tmp_path):
    df = sim.load_evaluation_rows(_write_input(tmp_path, _base_rows()))
    before = df["market_tier"].copy(deep=True)

    _, relaxed = sim.simulate_variant(
        df, "relax_league_profile_suppression", {"LEAGUE_PROFILE_SUPPRESSION"}, "Ligue 1"
    )

    assert len(relaxed) == 20
    assert df["market_tier"].equals(before)


def test_simulates_relax_all_ligue1_source_candidates(tmp_path):
    df = sim.load_evaluation_rows(_write_input(tmp_path, _base_rows()))
    summary = sim.build_variant_summary(df)
    row = summary[summary["variant_name"] == "relax_all_ligue1_source_candidates"].iloc[0]

    assert row["relaxed_rows"] == 60
    assert row["simulated_hard_no_go_n"] == 20


def test_a_tier_and_b_tier_counts_rates_remain_unchanged_in_all_variants(tmp_path):
    df = sim.load_evaluation_rows(_write_input(tmp_path, _base_rows()))
    summary = sim.build_variant_summary(df)

    assert set(summary["a_tier_n_unchanged"]) == {20}
    assert set(summary["a_tier_rate_unchanged"]) == {0.9}
    assert set(summary["b_tier_n_unchanged"]) == {20}
    assert set(summary["b_tier_rate_unchanged"]) == {0.85}


def test_recommended_market_type_and_subtype_remain_unchanged(tmp_path):
    df = sim.load_evaluation_rows(_write_input(tmp_path, _base_rows()))
    before = df[["recommended_market_type", "recommended_market_subtype"]].copy(deep=True)
    sim.simulate_variant(df, "relax_both_over25_btts", {"BOTH_OVER25_BTTS_PERMANENT_HARD_NO_GO"}, "Ligue 1")

    assert df[["recommended_market_type", "recommended_market_subtype"]].equals(before)


def test_recommendation_do_not_relax_when_no_variant_improves_target_rate(tmp_path):
    rows = []
    rows += _rows(20, 18, subtype="BOTH_OVER25_BTTS")
    rows += _rows(40, 36, subtype="OTHER")
    rows += _rows(20, 18, market_tier="A_TIER", subtype="UNDER_35", market_type="UNDER")
    rows += _rows(20, 18, market_tier="B_TIER", subtype="DOUBLE_CHANCE_1X", market_type="DOUBLE_CHANCE")
    df = sim.load_evaluation_rows(_write_input(tmp_path, rows))

    _, _, recommendation = sim.build_summary_table(df)

    assert recommendation == "DO_NOT_RELAX"


def test_recommendation_chooses_smallest_qualifying_variant(tmp_path):
    df = sim.load_evaluation_rows(_write_input(tmp_path, _base_rows()))

    _, _, recommendation = sim.build_summary_table(df)

    assert recommendation == "INVESTIGATE_RELAX_BOTH_OVER25_BTTS"


def test_recommendation_inconclusive_when_sample_is_too_small(tmp_path):
    rows = _rows(40, 20, subtype="BOTH_OVER25_BTTS")
    df = sim.load_evaluation_rows(_write_input(tmp_path, rows))

    _, _, recommendation = sim.build_summary_table(df)

    assert recommendation == "INCONCLUSIVE_MORE_REPLAY_REQUIRED"


def test_writes_csv_and_markdown(tmp_path):
    input_dir = _write_input(tmp_path, _base_rows())
    output_dir = tmp_path / "diagnostics"

    table, markdown = sim.run(input_dir=input_dir, output_dir=output_dir)

    assert not table.empty
    assert (output_dir / sim.OUTPUT_CSV).exists()
    assert (output_dir / sim.OUTPUT_MD).exists()
    assert "Phase 11.7 is simulation only. No tier rules were changed." in markdown
    assert "Simulation Recommendation" in markdown


def test_script_does_not_modify_protected_logic_files(tmp_path):
    protected = [
        ROOT / "src/football_prediction_v19/diagnostics/market_tier.py",
        ROOT / "src/football_prediction_v19/diagnostics/recommended_market.py",
        ROOT / "src/football_prediction_v19/model.py",
    ]
    before = {path: _hash(path) for path in protected}

    sim.run(input_dir=_write_input(tmp_path, _base_rows()), output_dir=tmp_path / "diagnostics")

    after = {path: _hash(path) for path in protected}
    assert after == before
