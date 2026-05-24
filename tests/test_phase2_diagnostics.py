# -*- coding: utf-8 -*-
"""Tests for Phase-2 diagnostic modules.

Covers:
  - miss_clusters.cluster_misses
  - calibration.reliability_diagram
  - drift.rolling_performance
  - market_tier league-relative score (LEAGUE_TIER_BASELINES + build_market_tier)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd
import pytest

# Ensure src/ is on the path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.diagnostics.miss_clusters import cluster_misses
from football_prediction_v19.diagnostics.calibration import reliability_diagram
from football_prediction_v19.diagnostics.drift import rolling_performance
from football_prediction_v19.diagnostics.market_tier import (
    build_market_tier,
    LEAGUE_TIER_BASELINES,
)


# ===========================================================================
# Helpers
# ===========================================================================

def _make_eval_df(
    n_hits: int,
    n_misses: int,
    league: str = "EPL",
    subtype: str = "UNDER_35",
    tier: str = "A_TIER",
    phase: str = "mid",
) -> pd.DataFrame:
    """Build a minimal evaluation DataFrame for miss-cluster / drift tests."""
    rows = []
    for _ in range(n_hits):
        rows.append({
            "league": league,
            "recommended_market_subtype": subtype,
            "market_tier": tier,
            "season_phase": phase,
            "type_success": True,
        })
    for _ in range(n_misses):
        rows.append({
            "league": league,
            "recommended_market_subtype": subtype,
            "market_tier": tier,
            "season_phase": phase,
            "type_success": False,
        })
    return pd.DataFrame(rows)


def _make_drift_df(
    n: int,
    hit_rate: float,
    start: str = "2024-01-01",
    date_col: str = "match_date",
) -> pd.DataFrame:
    """Build a minimal drift test DataFrame with daily rows.

    Hits are spread uniformly across rows using a repeating cycle so that
    every sub-window sees approximately the same hit rate (no spurious drift).
    """
    rows = []
    dates = pd.date_range(start=start, periods=n, freq="D")
    # Use a period-based repeating pattern: hits_per_cycle / cycle_len ≈ hit_rate
    # e.g. hit_rate=0.65 → 13/20 cycle
    cycle = 20
    hits_in_cycle = round(hit_rate * cycle)
    for i, d in enumerate(dates):
        success = (i % cycle) < hits_in_cycle
        rows.append({date_col: d, "type_success": success})
    return pd.DataFrame(rows)


def _make_minimal_rec(
    subtype: str = "UNDER_35",
    strength: str = "HIGH",
    league: str = "Premier League",
    chaos: float = 3.0,
) -> dict:
    return {
        "recommended_market_type":    "UNDER",
        "recommended_market_subtype": subtype,
        "recommended_market_read":    "under_35_profile",
        "league_adjusted_strength":   strength,
        "league":                     league,
        "confidence":                 "HIGH",
        "chaos_score_10":             chaos,
        "data_warning":               False,
        "league_profile":             "",
        "league_warning_flags":       "",
        "league_preferred_subtype":   "UNDER_35",
        "league_suppressed_subtype":  "",
    }


# ===========================================================================
# TestMissClusters (6 tests)
# ===========================================================================

class TestMissClusters:
    def test_empty_df_returns_empty(self):
        result = cluster_misses(pd.DataFrame())
        assert result.empty
        assert list(result.columns) == [
            "group_key", "n", "miss_count", "miss_rate", "warning_level"
        ]

    def test_filters_minimum_n_5(self):
        """Groups with fewer than 5 evaluated rows must be excluded."""
        df = _make_eval_df(n_hits=1, n_misses=3)  # total=4 < 5
        result = cluster_misses(df)
        assert result.empty, "Group of n=4 should be filtered out"

    def test_miss_rate_threshold_50_percent(self):
        """Groups with miss_rate < 0.50 must not appear."""
        df_below = _make_eval_df(n_hits=6, n_misses=4)  # miss_rate=0.40 < 0.50
        assert cluster_misses(df_below).empty

        df_above = _make_eval_df(n_hits=3, n_misses=7)  # miss_rate=0.70 >= 0.50
        assert not cluster_misses(df_above).empty

    def test_critical_flag_at_70_percent(self):
        """miss_rate >= 0.70 → CRITICAL; 0.50 <= rate < 0.70 → WARNING."""
        df_critical = _make_eval_df(n_hits=3, n_misses=7)   # 70%
        result_c = cluster_misses(df_critical)
        assert result_c["warning_level"].iloc[0] == "CRITICAL"

        df_warning = _make_eval_df(n_hits=4, n_misses=6)    # 60%
        result_w = cluster_misses(df_warning)
        assert result_w["warning_level"].iloc[0] == "WARNING"

    def test_correct_columns_in_output(self):
        df = _make_eval_df(n_hits=2, n_misses=8)
        result = cluster_misses(df)
        expected = {"group_key", "n", "miss_count", "miss_rate", "warning_level"}
        assert expected.issubset(set(result.columns))

    def test_sorted_by_miss_rate_desc(self):
        """Output must be sorted by miss_rate descending."""
        df = pd.concat([
            _make_eval_df(n_hits=2, n_misses=8, subtype="BTTS"),        # 80%
            _make_eval_df(n_hits=4, n_misses=6, subtype="OVER_25"),     # 60%
            _make_eval_df(n_hits=3, n_misses=7, subtype="UNDER_35"),    # 70%
        ])
        result = cluster_misses(df)
        assert len(result) >= 2
        rates = result["miss_rate"].tolist()
        assert rates == sorted(rates, reverse=True), "Not sorted by miss_rate DESC"


# ===========================================================================
# TestReliabilityDiagram (6 tests)
# ===========================================================================

class TestReliabilityDiagram:
    def test_perfect_calibration_ece_near_zero(self):
        """A perfectly calibrated model (pred = actual rate per bin) has ECE ≈ 0."""
        # Create data where each probability value equals the actual rate:
        # 50 obs at prob 0.2 → 10 hits (20% actual); 50 at 0.8 → 40 hits (80%)
        probs    = [0.2] * 50 + [0.8] * 50
        outcomes = [1] * 10 + [0] * 40 + [1] * 40 + [0] * 10
        df = reliability_diagram(probs, outcomes, n_bins=10)
        ece = df["ece"].iloc[0]
        assert ece < 0.05, f"ECE={ece:.4f} for a well-calibrated model should be near 0"

    def test_output_columns(self):
        probs    = [0.3, 0.5, 0.7] * 10
        outcomes = [0, 1, 1] * 10
        df = reliability_diagram(probs, outcomes)
        required = {"bin_center", "mean_pred_prob", "actual_rate", "n", "bin_low", "bin_high"}
        assert required.issubset(set(df.columns))

    def test_n_bins_respected(self):
        """Non-empty bins must be <= n_bins."""
        probs    = [i / 20 for i in range(20)]
        outcomes = [1 if p > 0.5 else 0 for p in probs]
        for nb in [5, 10, 20]:
            df = reliability_diagram(probs, outcomes, n_bins=nb)
            assert len(df) <= nb, f"Got {len(df)} bins, expected <= {nb}"

    def test_empty_bins_excluded(self):
        """Bins with no observations must not appear in the output."""
        # All probs in [0.4, 0.6] → bins outside this range are empty
        probs    = [0.45, 0.50, 0.55] * 10
        outcomes = [1, 0, 1] * 10
        df = reliability_diagram(probs, outcomes, n_bins=10)
        # Every row in output must have n >= 1
        assert (df["n"] >= 1).all()

    def test_ece_range_0_to_1(self):
        """ECE must always be in [0, 1]."""
        probs    = [0.9] * 20
        outcomes = [0] * 20  # severely overconfident
        df = reliability_diagram(probs, outcomes)
        ece = df["ece"].iloc[0]
        assert 0.0 <= ece <= 1.0

    def test_overconfident_model_high_ece(self):
        """A model predicting 0.9 when true rate is 0.1 should have high ECE."""
        probs    = [0.9] * 50
        outcomes = [1] * 5 + [0] * 45  # actual rate = 10%
        df = reliability_diagram(probs, outcomes)
        ece = df["ece"].iloc[0]
        assert ece > 0.5, f"Overconfident model ECE={ece:.4f} should be > 0.5"


# ===========================================================================
# TestDriftMonitor (5 tests)
# ===========================================================================

class TestDriftMonitor:
    def test_empty_df_returns_empty(self):
        result = rolling_performance(pd.DataFrame())
        assert result.empty
        expected_cols = {"window_start", "window_end", "n", "hit_rate", "overall_rate", "drift_flag"}
        assert expected_cols.issubset(set(result.columns))

    def test_no_drift_stable_performance(self):
        """Perfectly alternating True/False gives exactly 50% in every window.

        Since the per-window hit rate always equals the overall rate, the delta
        is always 0 — well inside the 8 pp DRIFT_WARNING threshold.
        """
        n = 100
        df = pd.DataFrame({
            "match_date":   pd.date_range("2024-01-01", periods=n, freq="D"),
            "type_success": [True, False] * (n // 2),
        })
        result = rolling_performance(df, window_weeks=4)
        assert result["drift_flag"].eq("DRIFT_WARNING").sum() == 0, (
            "Perfectly alternating data should not produce any DRIFT_WARNING"
        )

    def test_drift_warning_fires(self):
        """A window 10 pp below overall should trigger DRIFT_WARNING."""
        # First 80 rows: all misses (0%); last 80 rows: all hits (100%)
        # Overall ≈ 50%; early window ≈ 0% → delta = 50pp > 8pp threshold
        n = 160
        dates = pd.date_range("2024-01-01", periods=n, freq="D")
        rows = [{"match_date": d, "type_success": (i >= 80)} for i, d in enumerate(dates)]
        df = pd.DataFrame(rows)
        result = rolling_performance(df, window_weeks=4)
        assert result["drift_flag"].eq("DRIFT_WARNING").any(), (
            "Expected at least one DRIFT_WARNING when early windows have 0% hit rate"
        )

    def test_output_columns(self):
        df = _make_drift_df(n=60, hit_rate=0.5)
        result = rolling_performance(df, window_weeks=4)
        required = {"window_start", "window_end", "n", "hit_rate", "overall_rate", "drift_flag"}
        assert required.issubset(set(result.columns))

    def test_window_count(self):
        """Spanning 12 weeks of daily data with an 4-week window should yield several windows."""
        df = _make_drift_df(n=84, hit_rate=0.6)  # 84 days ≈ 12 weeks
        result = rolling_performance(df, window_weeks=4)
        # At least a few non-overlapping week windows
        assert len(result) >= 3


# ===========================================================================
# TestLeagueRelativeScore (4 tests)
# ===========================================================================

class TestLeagueRelativeScore:
    def test_known_league_returns_float(self):
        rec = _make_minimal_rec(league="Premier League")
        result = build_market_tier(rec)
        val = result.get("market_tier_score_league_relative")
        assert isinstance(val, float), f"Expected float, got {type(val)}"

    def test_unknown_league_returns_none(self):
        rec = _make_minimal_rec(league="Obscure League XYZ")
        result = build_market_tier(rec)
        val = result.get("market_tier_score_league_relative")
        assert val is None, f"Expected None for unknown league, got {val!r}"

    def test_z_score_formula_correct(self):
        """(score - mean) / std, rounded to 2 dp."""
        league = "Eredivisie"
        baseline = LEAGUE_TIER_BASELINES[league]
        rec = _make_minimal_rec(league=league)
        result = build_market_tier(rec)

        raw_score = result["market_tier_score"]
        expected_z = round((raw_score - baseline["mean"]) / baseline["std"], 2)
        actual_z   = result["market_tier_score_league_relative"]
        assert actual_z == expected_z, (
            f"Expected z={expected_z}, got {actual_z} "
            f"(raw_score={raw_score}, baseline={baseline})"
        )

    def test_rounded_to_2_decimals(self):
        """The league-relative score must have at most 2 decimal places."""
        for league in LEAGUE_TIER_BASELINES:
            rec = _make_minimal_rec(league=league)
            result = build_market_tier(rec)
            val = result.get("market_tier_score_league_relative")
            if val is None:
                continue
            # Check <= 2 decimal places by round-tripping
            assert round(val, 2) == val, (
                f"League {league}: value {val} has more than 2 decimal places"
            )
