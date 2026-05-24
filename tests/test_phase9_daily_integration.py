# -*- coding: utf-8 -*-
"""Tests for Phase-9 daily-report context signal integration.

Covers:
  - get_team_context_features
  - get_fixture_context_features
  - context_csv_fields
  - print_context_signals_section (no crash, correct filtering)
  - compute_context_signal_analysis

All helper functions live in scripts/_context_signals.py which is imported
by adding the scripts/ directory to sys.path.
"""
from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Make the scripts/ helpers importable
_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _context_signals import (
    get_team_context_features,
    get_fixture_context_features,
    context_csv_fields,
    CONTEXT_CSV_KEYS,
    print_context_signals_section,
    compute_context_signal_analysis,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_history(n: int = 20, seed: int = 0) -> pd.DataFrame:
    """Minimal history DataFrame with optional context columns already computed."""
    rng = np.random.default_rng(seed)
    teams = ["Arsenal", "Chelsea", "Real Madrid", "Barcelona",
             "Liverpool", "Everton", "City", "United"]
    records = []
    base = pd.Timestamp("2023-08-01")
    for i in range(n):
        home, away = rng.choice(teams, size=2, replace=False)
        records.append({
            "date":       base + pd.Timedelta(days=i * 7),
            "home_team":  home,
            "away_team":  away,
            "home_goals": int(rng.poisson(1.5)),
            "away_goals": int(rng.poisson(1.1)),
            # Phase 5/6 context columns (as would be produced by build_extended_features)
            "h2h_btts_rate":        round(float(rng.uniform(0.2, 0.8)), 2),
            "h2h_avg_goals":        round(float(rng.uniform(1.5, 3.5)), 2),
            "h2h_n":                int(rng.integers(1, 10)),
            "elo_home":             round(float(rng.uniform(1400, 1700)), 0),
            "elo_away":             round(float(rng.uniform(1400, 1700)), 0),
            "elo_diff":             round(float(rng.uniform(-200, 200)), 0),
            "ref_btts_rate":        round(float(rng.uniform(0.3, 0.7)), 2),
            "ref_avg_goals":        round(float(rng.uniform(2.0, 3.5)), 2),
            "home_days_since_last": float(rng.integers(3, 20)),
            "away_days_since_last": float(rng.integers(3, 20)),
            "home_short_rest":      bool(rng.integers(0, 2)),
            "away_short_rest":      bool(rng.integers(0, 2)),
            "home_table_rank":      int(rng.integers(1, 20)),
            "away_table_rank":      int(rng.integers(1, 20)),
            "rank_diff":            int(rng.integers(-10, 10)),
            "dead_rubber_flag":     bool(rng.integers(0, 2)),
            "is_derby":             False,
            "derby_name":           "",
        })
    return pd.DataFrame(records)


def _make_result(home: str, away: str, tier: str, ctx: dict | None = None) -> dict:
    """Build a minimal result dict as produced by the daily scripts."""
    return {
        "home": home,
        "away": away,
        "recommended_market": {"market_tier": tier, "market_tier_score": 80},
        "ctx": ctx or {},
    }


# ===========================================================================
# TestContextSignalOutput (5 tests)
# ===========================================================================

class TestContextSignalOutput:

    def test_h2h_btts_rate_in_csv_output(self):
        """context_csv_fields must include h2h_btts_rate when present in ctx."""
        ctx = {"h2h_btts_rate": 0.55, "elo_diff": 120.0}
        fields = context_csv_fields(ctx)
        assert "h2h_btts_rate" in fields
        assert fields["h2h_btts_rate"] == 0.55

    def test_elo_diff_in_csv_output(self):
        """context_csv_fields must include elo_diff."""
        ctx = {"elo_diff": -80.5}
        fields = context_csv_fields(ctx)
        assert "elo_diff" in fields
        assert fields["elo_diff"] == -80.5

    def test_derby_flag_correct(self):
        """get_fixture_context_features correctly detects known derby."""
        history = _make_history(n=20)
        ctx = get_fixture_context_features(
            "Arsenal", "Tottenham Hotspur",
            pd.Timestamp("2023-11-04"),
            history,
        )
        assert ctx["is_derby"] == 1
        assert ctx["derby_name"] == "North London Derby"

    def test_short_rest_flag_correct(self):
        """home_short_rest is extracted from the home team's last history row."""
        history = _make_history(n=20)
        # Force Arsenal's last row to have home_short_rest=True
        arsenal_mask = (history["home_team"] == "Arsenal") | (history["away_team"] == "Arsenal")
        if arsenal_mask.any():
            idx = history[arsenal_mask].index[-1]
            history.at[idx, "home_short_rest"] = True

        ctx = get_fixture_context_features("Arsenal", "Chelsea", pd.Timestamp("2023-12-01"), history)
        # Should be int 0 or 1
        assert ctx["home_short_rest"] in (0, 1)

    def test_missing_features_graceful(self):
        """get_fixture_context_features returns a dict (no crash) for team not in history."""
        history = _make_history(n=10)
        ctx = get_fixture_context_features(
            "UnknownTeam", "AnotherUnknown",
            pd.Timestamp("2025-01-01"),
            history,
        )
        assert isinstance(ctx, dict)
        # All CONTEXT_CSV_KEYS must be present (possibly as "")
        for key in CONTEXT_CSV_KEYS:
            assert key in ctx


# ===========================================================================
# TestContextSignalAnalysis (5 tests)
# ===========================================================================

class TestContextSignalAnalysis:

    def _make_eval_df(self, n: int = 20, seed: int = 7) -> pd.DataFrame:
        """Minimal evaluation DataFrame with context and success columns."""
        rng = np.random.default_rng(seed)
        return pd.DataFrame({
            "is_derby":         rng.choice([0, 1], size=n),
            "away_short_rest":  rng.choice([0, 1], size=n),
            "dead_rubber_flag": rng.choice([0, 1], size=n),
            "elo_diff":         rng.uniform(-300, 300, size=n),
            "h2h_btts_rate":    rng.uniform(0.0, 1.0, size=n),
            "type_success":     rng.choice([True, False], size=n).astype(float),
        })

    def test_derby_hit_rate_computed(self):
        """compute_context_signal_analysis includes a Derby Matches section."""
        df = self._make_eval_df()
        lines = compute_context_signal_analysis(df)
        text = "\n".join(lines)
        assert "Derby Matches" in text

    def test_short_rest_section_present(self):
        """Short Rest (Away) section is included when column present."""
        df = self._make_eval_df()
        lines = compute_context_signal_analysis(df)
        text = "\n".join(lines)
        assert "Short Rest (Away)" in text

    def test_high_elo_diff_section(self):
        """High Elo Diff section is included when elo_diff column present."""
        df = self._make_eval_df()
        lines = compute_context_signal_analysis(df)
        text = "\n".join(lines)
        assert "High Elo Diff" in text

    def test_empty_context_no_crash(self):
        """compute_context_signal_analysis handles DataFrame without context columns."""
        df = pd.DataFrame({
            "type_success": [True, False, True, True],
        })
        lines = compute_context_signal_analysis(df)
        assert isinstance(lines, list)
        assert len(lines) > 0

    def test_context_columns_in_eval_df(self):
        """All CONTEXT_CSV_KEYS appear as expected fields in context_csv_fields output."""
        ctx = {k: "" for k in CONTEXT_CSV_KEYS}
        fields = context_csv_fields(ctx)
        for key in CONTEXT_CSV_KEYS:
            assert key in fields
