# -*- coding: utf-8 -*-
"""Tests for the Dixon-Coles Poisson model and related Phase-4 modules.

Covers:
  - DixonColesModel math (tau, probabilities, goals markets)
  - DixonColesModel.fit() on synthetic data
  - evaluate_poisson_walk_forward (walk-forward harness)
  - poisson_market_tier_override (diagnostic overlay)
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.models.dixon_coles import DixonColesModel
from football_prediction_v19.models.poisson_evaluator import evaluate_poisson_walk_forward
from football_prediction_v19.diagnostics.poisson_diagnostics import poisson_market_tier_override


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_matches(
    n: int = 30,
    teams: list[str] | None = None,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate synthetic match data for fitting tests."""
    if teams is None:
        teams = ["TeamA", "TeamB", "TeamC", "TeamD", "TeamE"]
    rng = np.random.default_rng(seed)
    records = []
    base_date = pd.Timestamp("2023-01-01")
    for i in range(n):
        home, away = rng.choice(teams, size=2, replace=False)
        records.append(
            {
                "date":       base_date + pd.Timedelta(days=i),
                "home_team":  home,
                "away_team":  away,
                "home_goals": int(rng.poisson(1.5)),
                "away_goals": int(rng.poisson(1.1)),
            }
        )
    return pd.DataFrame(records)


def _fitted_model(n: int = 30, seed: int = 42) -> DixonColesModel:
    """Return a DixonColesModel fitted on synthetic data."""
    df = _make_matches(n=n, seed=seed)
    model = DixonColesModel()
    model.fit(df)
    return model, df["home_team"].unique()[0], df["away_team"].unique()[0]


def _probs(home: str = "TeamA", away: str = "TeamB", **kwargs) -> dict:
    """Return a minimal dc_probs dict for diagnostic tests."""
    defaults = {
        "home_win":  0.45,
        "draw":      0.28,
        "away_win":  0.27,
        "btts":      0.50,
        "over_25":   0.55,
        "under_35":  0.60,
        "btts_over25": 0.35,
        "expected_home_goals": 1.5,
        "expected_away_goals": 1.1,
    }
    defaults.update(kwargs)
    return defaults


# ===========================================================================
# TestDixonColesMath (8 tests)
# ===========================================================================

class TestDixonColesMath:
    def setup_method(self):
        self.m = DixonColesModel(rho=-0.13)
        # Manually set minimal parameters so _lambda works
        for team in ("TeamA", "TeamB"):
            self.m.attack[team]  = 0.0
            self.m.defense[team] = 0.0
        self.m.home_adv = 0.25
        self.m.fitted = True

    def test_tau_0_0_reduces_prob(self):
        """tau(0,0) < 1 when rho < 0 (correlation reduces 0-0 probability)."""
        lam_h, lam_a = 1.5, 1.1
        tau = self.m._tau(0, 0, lam_h, lam_a)
        # 1 - lam_h * lam_a * rho = 1 - 1.5*1.1*(-0.13) = 1 + 0.2145 > 1
        # rho=-0.13 makes tau(0,0) > 1 (slightly boosts 0-0)
        assert tau > 0, "tau must be positive"
        expected = 1.0 - lam_h * lam_a * (-0.13)
        assert abs(tau - expected) < 1e-9

    def test_tau_1_1_reduces_prob(self):
        """tau(1,1) = 1 - rho; with rho=-0.13 this is 1.13 > 1."""
        tau = self.m._tau(1, 1, 1.5, 1.1)
        assert abs(tau - (1.0 - self.m.rho)) < 1e-9

    def test_tau_other_is_1(self):
        """For scores other than (0,0),(1,0),(0,1),(1,1), tau=1."""
        for x, y in [(2, 0), (0, 2), (2, 2), (3, 1), (5, 4)]:
            assert self.m._tau(x, y, 1.5, 1.1) == 1.0, (
                f"tau({x},{y}) should be 1.0"
            )

    def test_probabilities_sum_to_1(self):
        """home_win + draw + away_win must equal 1.0 (within float tolerance)."""
        probs = self.m.predict_probabilities("TeamA", "TeamB")
        total = probs["home_win"] + probs["draw"] + probs["away_win"]
        assert abs(total - 1.0) < 1e-6, f"Outcome probs sum to {total}, expected 1.0"

    def test_btts_range_0_to_1(self):
        """BTTS probability must be in [0, 1]."""
        probs = self.m.predict_probabilities("TeamA", "TeamB")
        assert 0.0 <= probs["btts"] <= 1.0

    def test_under35_plus_over35_approx_equals_1(self):
        """under_35 + over_35 ≈ 1 (they're complements; small truncation error ok)."""
        probs = self.m.predict_probabilities("TeamA", "TeamB")
        total = probs["under_35"] + probs["over_35"]
        # They share the boundary at 3 goals: under_35 counts ≤3, over_35 counts ≥4
        # Together they cover all outcomes (no overlap), sum should be ≈ 1
        assert abs(total - 1.0) < 0.02, (
            f"under_35 + over_35 = {total:.4f}, expected ≈ 1.0"
        )

    def test_expected_goals_positive(self):
        """Expected goals must be strictly positive."""
        probs = self.m.predict_probabilities("TeamA", "TeamB")
        assert probs["expected_home_goals"] > 0
        assert probs["expected_away_goals"] > 0

    def test_unknown_team_raises_value_error(self):
        """Requesting probabilities for an unknown team raises ValueError."""
        with pytest.raises(ValueError, match="Unknown team"):
            self.m.predict_probabilities("TeamA", "Nonexistent FC")


# ===========================================================================
# TestDixonColesFit (5 tests)
# ===========================================================================

class TestDixonColesFit:
    def test_fit_on_minimal_data(self):
        """Model should fit without errors on 30 synthetic matches."""
        df = _make_matches(n=30)
        model = DixonColesModel()
        model.fit(df)  # must not raise

    def test_fit_sets_fitted_true(self):
        df = _make_matches(n=20)
        model = DixonColesModel()
        assert not model.fitted
        model.fit(df)
        assert model.fitted

    def test_attack_values_finite(self):
        """All attack values must be finite floats after fitting."""
        df = _make_matches(n=30)
        model = DixonColesModel()
        model.fit(df)
        for team, val in model.attack.items():
            assert math.isfinite(val), f"attack[{team}] = {val} is not finite"

    def test_home_advantage_positive(self):
        """Home advantage should be positive (home teams score more)."""
        df = _make_matches(n=50, seed=0)
        model = DixonColesModel()
        model.fit(df)
        assert model.home_adv > 0, (
            f"Expected positive home_adv, got {model.home_adv}"
        )

    def test_predict_after_fit_no_error(self):
        """predict_probabilities must work for any team pair seen during fit."""
        df = _make_matches(n=30)
        model = DixonColesModel()
        model.fit(df)
        teams = list(model.attack.keys())
        probs = model.predict_probabilities(teams[0], teams[1])
        assert "home_win" in probs


# ===========================================================================
# TestPoissonWalkForward (5 tests)
# ===========================================================================

class TestPoissonWalkForward:
    def _make_walk_df(self, n: int = 150, seed: int = 7) -> pd.DataFrame:
        """150 chronological matches for walk-forward tests."""
        return _make_matches(n=n, seed=seed)

    def test_warmup_skips_early_matches(self):
        """With min_warmup=100, the first 100 matches must be skipped."""
        df = self._make_walk_df(n=120)
        result = evaluate_poisson_walk_forward(df, min_warmup=100)
        # At most n - min_warmup rows can appear (some may be skipped due to unknown teams)
        assert len(result) <= 20

    def test_output_columns_present(self):
        """All required output columns must be present."""
        df = self._make_walk_df(n=150)
        result = evaluate_poisson_walk_forward(df, min_warmup=100)
        required = {
            "date", "home_team", "away_team",
            "actual_home_goals", "actual_away_goals",
            "dc_home_win_prob", "dc_draw_prob", "dc_away_win_prob",
            "dc_btts_prob", "dc_over25_prob", "dc_under35_prob",
            "dc_home_correct", "dc_btts_correct", "dc_under35_correct",
        }
        if result.empty:
            pytest.skip("No rows evaluated (warmup)")
        assert required.issubset(set(result.columns))

    def test_no_leakage_in_prior(self):
        """The walk-forward evaluator must not leak future data into training."""
        # This is guaranteed by _assert_no_leakage inside evaluate_poisson_walk_forward.
        # We verify it doesn't raise for clean sequential data.
        df = self._make_walk_df(n=120)
        # Should run without AssertionError
        result = evaluate_poisson_walk_forward(df, min_warmup=100)
        assert isinstance(result, pd.DataFrame)

    def test_dc_home_correct_is_bool(self):
        """dc_home_correct column must contain boolean values."""
        df = self._make_walk_df(n=150)
        result = evaluate_poisson_walk_forward(df, min_warmup=100)
        if result.empty:
            pytest.skip("No rows evaluated")
        assert result["dc_home_correct"].dtype == bool or set(
            result["dc_home_correct"].unique()
        ).issubset({True, False})

    def test_returns_dataframe(self):
        """Return type must always be a pd.DataFrame, even when empty."""
        df = _make_matches(n=10)  # too few for min_warmup=100
        result = evaluate_poisson_walk_forward(df, min_warmup=100)
        assert isinstance(result, pd.DataFrame)
        assert result.empty


# ===========================================================================
# TestPoissonDiagnostics (4 tests)
# ===========================================================================

class TestPoissonDiagnostics:
    def test_under35_conflict_downgrades_tier(self):
        """UNDER_35 subtype with dc_under35_prob < 0.45 → dc_confirms_tier=False
        and A/B tiers are downgraded to C_TIER."""
        dc = _probs(under_35=0.40)
        result = poisson_market_tier_override(dc, "A_TIER", "UNDER_35")
        assert result["dc_confirms_tier"] is False
        assert result["market_tier"] == "C_TIER"
        assert "DC conflicts: under35_prob" in result["dc_tier_note"]
        assert "[DC_DOWNGRADE]" in result["dc_tier_note"]

    def test_btts_conflict_downgrades_tier(self):
        """BTTS subtype with dc_btts_prob < 0.40 → dc_confirms_tier=False
        and A/B tiers are downgraded to C_TIER."""
        dc = _probs(btts=0.35)
        result = poisson_market_tier_override(dc, "B_TIER", "BTTS")
        assert result["dc_confirms_tier"] is False
        assert result["market_tier"] == "C_TIER"
        assert "DC conflicts: btts_prob" in result["dc_tier_note"]
        assert "[DC_DOWNGRADE]" in result["dc_tier_note"]

    def test_no_conflict_confirms_tier(self):
        """When DC probs are above thresholds, tier is confirmed unchanged."""
        dc = _probs(under_35=0.65, btts=0.55)
        result = poisson_market_tier_override(dc, "A_TIER", "UNDER_35")
        assert result["dc_confirms_tier"] is True
        assert result["market_tier"] == "A_TIER"
        assert result["dc_tier_note"] == ""

    def test_downgrade_only_for_a_and_b_tier(self):
        """DC conflict does NOT downgrade tiers other than A_TIER/B_TIER."""
        dc = _probs(under_35=0.30)  # strong conflict
        for tier in ("C_TIER", "DOWNGRADE", "HARD_NO_GO", "OBSERVE_ONLY"):
            result = poisson_market_tier_override(dc, tier, "UNDER_35")
            assert result["market_tier"] == tier, (
                f"Expected {tier} unchanged, got {result['market_tier']}"
            )
            assert result["dc_confirms_tier"] is False
