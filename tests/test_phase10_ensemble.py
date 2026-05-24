# -*- coding: utf-8 -*-
"""Tests for Phase-10 ensemble predictor and tier override.

Covers:
  - EnsemblePredictor (fit, predict_proba_all, agreement, etc.)
  - apply_ensemble_override (all tier rules)
  - Integration checks (return-dict keys, SUPER_A_TIER guard)

All helpers live in:
  src/football_prediction_v19/models/ensemble.py
  src/football_prediction_v19/diagnostics/ensemble_tier.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression

# Make src/ importable
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from football_prediction_v19.models.ensemble import EnsemblePredictor
from football_prediction_v19.diagnostics.ensemble_tier import apply_ensemble_override


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_binary_data(n: int = 120, seed: int = 0):
    """Simple 2-class dataset for fast fitting."""
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((n, 4))
    y = (X[:, 0] + X[:, 1] > 0).astype(int)
    return X, y


def _make_three_class_data(n: int = 180, seed: int = 1):
    """Simple 3-class dataset (H/D/A stand-in)."""
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((n, 4))
    y = np.array(["H", "D", "A"] * (n // 3))
    return X, y


class _FixedPredictor:
    """Dummy classifier that always predicts a fixed class probabilities."""

    def __init__(self, proba_row: list[float]) -> None:
        self._proba = np.array(proba_row, dtype=float)
        self.classes_ = np.arange(len(proba_row))

    def fit(self, X, y):
        return self

    def predict_proba(self, X):
        n = len(X) if hasattr(X, "__len__") else 1
        return np.tile(self._proba, (n, 1))


# ===========================================================================
# TestEnsemblePredictor (6 tests)
# ===========================================================================

class TestEnsemblePredictor:

    def test_fit_sets_fitted_true(self):
        """fit() must set self.fitted to True."""
        X, y = _make_binary_data()
        ep = EnsemblePredictor()
        assert ep.fitted is False
        ep.fit(X, y)
        assert ep.fitted is True

    def test_predict_proba_all_keys_present(self):
        """predict_proba_all must return dict with all required keys."""
        X, y = _make_three_class_data()
        ep = EnsemblePredictor()
        ep.fit(X, y)
        result = ep.predict_proba_all(X[:1])
        for key in ("lr", "gb", "rf", "ensemble", "agreement"):
            assert key in result, f"Missing key: {key}"
        assert result["ensemble"].shape == result["lr"].shape

    def test_agreement_full_consensus(self):
        """All three models predict the same class → agreement == 1.0."""
        # Identical models always predict class 0 with probability 1.0
        models = [
            _FixedPredictor([1.0, 0.0, 0.0]),
            _FixedPredictor([1.0, 0.0, 0.0]),
            _FixedPredictor([1.0, 0.0, 0.0]),
        ]
        ep = EnsemblePredictor(models=models)
        ep.fitted = True  # skip actual fit
        X = np.zeros((1, 1))
        assert ep.agreement_score(X) == 1.0

    def test_agreement_split(self):
        """Two models agree, one disagrees → agreement == 0.5."""
        models = [
            _FixedPredictor([1.0, 0.0, 0.0]),   # predicts class 0
            _FixedPredictor([1.0, 0.0, 0.0]),   # predicts class 0
            _FixedPredictor([0.0, 1.0, 0.0]),   # predicts class 1
        ]
        ep = EnsemblePredictor(models=models)
        ep.fitted = True
        X = np.zeros((1, 1))
        assert ep.agreement_score(X) == 0.5

    def test_agreement_no_consensus(self):
        """All three models predict different classes → agreement == 0.0."""
        models = [
            _FixedPredictor([1.0, 0.0, 0.0]),   # predicts class 0
            _FixedPredictor([0.0, 1.0, 0.0]),   # predicts class 1
            _FixedPredictor([0.0, 0.0, 1.0]),   # predicts class 2
        ]
        ep = EnsemblePredictor(models=models)
        ep.fitted = True
        X = np.zeros((1, 1))
        assert ep.agreement_score(X) == 0.0

    def test_not_fitted_raises_runtime_error(self):
        """predict_proba_all before fit() must raise RuntimeError."""
        ep = EnsemblePredictor()
        X = np.zeros((2, 3))
        with pytest.raises(RuntimeError):
            ep.predict_proba_all(X)


# ===========================================================================
# TestEnsembleTierOverride (7 tests)
# ===========================================================================

class TestEnsembleTierOverride:

    def test_consensus_a_tier_becomes_super_a(self):
        """agreement==1.0 + A_TIER → SUPER_A_TIER."""
        result = apply_ensemble_override("A_TIER", 85, 1.0, {})
        assert result["market_tier"] == "SUPER_A_TIER"
        assert "SUPER_A_TIER" in result["market_tier_flags"]
        assert "[ENSEMBLE_CONSENSUS]" in result["market_tier_reason"]
        assert result["ensemble_note"] == "CONSENSUS"

    def test_disagreement_a_tier_becomes_c(self):
        """agreement==0.0 + A_TIER → C_TIER."""
        result = apply_ensemble_override("A_TIER", 80, 0.0, {})
        assert result["market_tier"] == "C_TIER"
        assert "ENSEMBLE_DISAGREEMENT" in result["market_tier_flags"]
        assert result["ensemble_note"] == "DISAGREEMENT"

    def test_disagreement_b_tier_becomes_c(self):
        """agreement==0.0 + B_TIER → C_TIER."""
        result = apply_ensemble_override("B_TIER", 65, 0.0, {})
        assert result["market_tier"] == "C_TIER"
        assert "ENSEMBLE_DISAGREEMENT" in result["market_tier_flags"]

    def test_split_adds_flag_only(self):
        """agreement==0.5 → tier unchanged, ENSEMBLE_SPLIT flag added."""
        result = apply_ensemble_override("A_TIER", 82, 0.5, {})
        assert result["market_tier"] == "A_TIER"
        assert "ENSEMBLE_SPLIT" in result["market_tier_flags"]
        assert result["ensemble_note"] == "SPLIT"

    def test_hard_no_go_never_upgraded(self):
        """HARD_NO_GO must be preserved regardless of agreement."""
        for agreement in (0.0, 0.5, 1.0):
            result = apply_ensemble_override("HARD_NO_GO", 20, agreement, {})
            assert result["market_tier"] == "HARD_NO_GO", (
                f"HARD_NO_GO was changed for agreement={agreement}"
            )
            assert "SUPER_A_TIER" not in result["market_tier_flags"]

    def test_c_tier_not_upgraded_by_consensus(self):
        """consensus on C_TIER must NOT produce SUPER_A_TIER (rule 2 is A_TIER only)."""
        result = apply_ensemble_override("C_TIER", 40, 1.0, {})
        assert result["market_tier"] == "C_TIER"
        assert "SUPER_A_TIER" not in result["market_tier_flags"]
        assert result["ensemble_note"] == "CONSENSUS"

    def test_ensemble_note_values_correct(self):
        """ensemble_note must be CONSENSUS / SPLIT / DISAGREEMENT depending on agreement."""
        assert apply_ensemble_override("B_TIER", 60, 1.0, {})["ensemble_note"] == "CONSENSUS"
        assert apply_ensemble_override("B_TIER", 60, 0.5, {})["ensemble_note"] == "SPLIT"
        assert apply_ensemble_override("C_TIER", 50, 0.0, {})["ensemble_note"] == "DISAGREEMENT"


# ===========================================================================
# TestEnsembleIntegration (2 tests)
# ===========================================================================

class TestEnsembleIntegration:

    def test_override_dict_has_required_keys(self):
        """apply_ensemble_override must always return all five required keys."""
        required = {
            "market_tier",
            "market_tier_reason",
            "market_tier_flags",
            "ensemble_agreement",
            "ensemble_note",
        }
        for tier in ("A_TIER", "B_TIER", "C_TIER", "HARD_NO_GO", "DOWNGRADE"):
            for agreement in (0.0, 0.5, 1.0):
                result = apply_ensemble_override(tier, 50, agreement, {})
                missing = required - set(result.keys())
                assert not missing, (
                    f"Missing keys {missing} for tier={tier}, agreement={agreement}"
                )

    def test_super_a_tier_only_from_a_tier(self):
        """SUPER_A_TIER can only be produced from A_TIER + agreement==1.0."""
        non_a_tiers = ["B_TIER", "C_TIER", "HARD_NO_GO", "DOWNGRADE", "OBSERVE_ONLY"]
        for tier in non_a_tiers:
            result = apply_ensemble_override(tier, 50, 1.0, {})
            assert result["market_tier"] != "SUPER_A_TIER", (
                f"SUPER_A_TIER incorrectly produced from {tier}"
            )
        # A_TIER + consensus → SUPER_A_TIER
        result = apply_ensemble_override("A_TIER", 90, 1.0, {})
        assert result["market_tier"] == "SUPER_A_TIER"
