"""Tests for the MLS Away paper-test filter.

Validates the strict inclusion/exclusion gates:
- Home picks excluded
- Draw picks excluded
- Away edge < 0.04 excluded
- Away edge >= 0.04 included
- Missing odds excluded
- Missing away edge excluded
- Stake is always 1.0
- Chaos gate
- Control gate
- Non-MLS excluded
"""

import numpy as np
import pandas as pd
import pytest

from football_prediction_v19.paper_test.mls_away_filter import (
    STAKE,
    filter_candidates,
    _is_mls_away_candidate,
)


def _row(
    league="MLS",
    value_pick="Away",
    odds_away=3.50,
    edge_away=0.05,
    control_score=7.5,
    chaos_score=5.0,
    prob_away=0.35,
    result="",
    profit=np.nan,
) -> dict:
    return {
        "league": league,
        "value_pick": value_pick,
        "odds_away": odds_away,
        "edge_away": edge_away,
        "control_score": control_score,
        "chaos_score": chaos_score,
        "prob_away": prob_away,
        "date": "2025-06-01",
        "home_team": "LA Galaxy",
        "away_team": "Portland Timbers",
        "result": result,
        "profit": profit,
    }


def _df(*rows) -> pd.DataFrame:
    return pd.DataFrame(list(rows))


# ── Inclusion ──────────────────────────────────────────────────────────────


def test_valid_away_candidate_included():
    df = _df(_row())
    out = filter_candidates(df)
    assert len(out) == 1
    assert out.iloc[0]["pick"] == "Away"


def test_away_edge_exactly_at_threshold_included():
    df = _df(_row(edge_away=0.04))
    out = filter_candidates(df, min_edge=0.04)
    assert len(out) == 1


# ── Exclusions ─────────────────────────────────────────────────────────────


def test_home_pick_excluded():
    df = _df(_row(value_pick="Home"))
    out = filter_candidates(df)
    assert len(out) == 0


def test_draw_pick_excluded():
    df = _df(_row(value_pick="Draw"))
    out = filter_candidates(df)
    assert len(out) == 0


def test_away_edge_below_threshold_excluded():
    df = _df(_row(edge_away=0.039))
    out = filter_candidates(df, min_edge=0.04)
    assert len(out) == 0


def test_missing_odds_away_excluded():
    df = _df(_row(odds_away=np.nan))
    out = filter_candidates(df)
    assert len(out) == 0


def test_zero_odds_away_excluded():
    df = _df(_row(odds_away=0.0))
    out = filter_candidates(df)
    assert len(out) == 0


def test_missing_edge_away_excluded():
    df = _df(_row(edge_away=np.nan))
    out = filter_candidates(df)
    assert len(out) == 0


def test_control_below_threshold_excluded():
    df = _df(_row(control_score=6.9))
    out = filter_candidates(df, min_control=7.0)
    assert len(out) == 0


def test_chaos_above_threshold_excluded():
    df = _df(_row(chaos_score=7.1))
    out = filter_candidates(df, max_chaos=7.0)
    assert len(out) == 0


def test_non_mls_excluded():
    df = _df(_row(league="Premier League"))
    out = filter_candidates(df)
    assert len(out) == 0


# ── Stake ──────────────────────────────────────────────────────────────────


def test_stake_is_always_1_unit():
    df = _df(_row(), _row(edge_away=0.08))
    out = filter_candidates(df)
    assert (out["stake"] == 1.0).all()


def test_stake_constant_is_1():
    assert STAKE == 1.0


# ── Status column ──────────────────────────────────────────────────────────


def test_status_pending_for_upcoming():
    df = _df(_row())
    out = filter_candidates(df, status="PENDING")
    assert out.iloc[0]["status"] == "PENDING"


def test_status_settled_for_historical():
    df = _df(_row(result="A", profit=2.50))
    out = filter_candidates(df, status="SETTLED")
    assert out.iloc[0]["status"] == "SETTLED"


# ── Profit calculation for historical rows ─────────────────────────────────


def test_profit_passed_through_from_backtest():
    df = _df(_row(result="A", profit=2.50))
    out = filter_candidates(df, status="SETTLED")
    assert out.iloc[0]["profit"] == pytest.approx(2.50)


def test_profit_negative_when_away_lost():
    df = _df(_row(result="H", profit=-1.0))
    out = filter_candidates(df, status="SETTLED")
    assert out.iloc[0]["profit"] == pytest.approx(-1.0)


# ── Output columns ─────────────────────────────────────────────────────────


def test_output_has_required_columns():
    df = _df(_row())
    out = filter_candidates(df)
    required = {
        "date", "league", "home_team", "away_team", "pick",
        "odds_away", "model_away_prob", "edge", "control_score",
        "chaos_score", "status", "stake", "result", "profit",
    }
    assert required.issubset(set(out.columns))


# ── Mixed batch ────────────────────────────────────────────────────────────


def test_mixed_batch_only_valid_away_kept():
    df = _df(
        _row(value_pick="Home"),           # excluded: Home
        _row(value_pick="Draw"),           # excluded: Draw
        _row(edge_away=0.02),              # excluded: low edge
        _row(odds_away=np.nan),            # excluded: no odds
        _row(league="Bundesliga"),         # excluded: wrong league
        _row(control_score=6.0),           # excluded: low control
        _row(chaos_score=8.0),             # excluded: high chaos
        _row(edge_away=0.04),              # INCLUDED
        _row(edge_away=0.07),              # INCLUDED
    )
    out = filter_candidates(df)
    assert len(out) == 2
    assert (out["pick"] == "Away").all()
    assert (out["stake"] == 1.0).all()


# ── _is_mls_away_candidate unit tests ─────────────────────────────────────


def test_is_candidate_returns_true_for_valid_row():
    assert _is_mls_away_candidate(pd.Series(_row())) is True


def test_is_candidate_false_for_home():
    assert _is_mls_away_candidate(pd.Series(_row(value_pick="Home"))) is False


def test_is_candidate_false_for_draw():
    assert _is_mls_away_candidate(pd.Series(_row(value_pick="Draw"))) is False


def test_is_candidate_false_for_low_edge():
    assert _is_mls_away_candidate(pd.Series(_row(edge_away=0.039)), min_edge=0.04) is False


def test_is_candidate_false_for_missing_odds():
    assert _is_mls_away_candidate(pd.Series(_row(odds_away=np.nan))) is False
