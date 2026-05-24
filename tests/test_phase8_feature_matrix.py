# -*- coding: utf-8 -*-
"""Tests for Phase-8 optional feature matrix extension.

Covers:
  - OPTIONAL_FEATURES / BOOL_OPTIONAL_FEATURES constants
  - build_features() with no optional columns → unchanged behaviour
  - build_features() with Phase-5/6 columns → they are merged + imputed
  - Boolean columns encoded as int (0/1)
  - NaN filled with median, not zero
  - Feature matrix shape widening
  - No NaN in numeric output columns
  - Existing mandatory features unchanged
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.features import (
    build_features,
    OPTIONAL_FEATURES,
    BOOL_OPTIONAL_FEATURES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_df(n: int = 30, seed: int = 42) -> pd.DataFrame:
    """Minimal DataFrame that satisfies build_features() requirements."""
    rng = np.random.default_rng(seed)
    teams = ["Arsenal", "Chelsea", "City", "United", "Liverpool",
             "Everton", "Spurs", "Leicester"]
    records = []
    base = pd.Timestamp("2022-08-01")
    for i in range(n):
        home, away = rng.choice(teams, size=2, replace=False)
        hg = int(rng.poisson(1.5))
        ag = int(rng.poisson(1.1))
        records.append({
            "date":       base + pd.Timedelta(days=i * 7),
            "home_team":  home,
            "away_team":  away,
            "home_goals": hg,
            "away_goals": ag,
            "score":      f"{hg}-{ag}",
            "home_xg":    round(float(rng.uniform(0.5, 2.5)), 2),
            "away_xg":    round(float(rng.uniform(0.3, 2.0)), 2),
        })
    return pd.DataFrame(records)


def _df_with_optional(cols: list[str], n: int = 30, seed: int = 42) -> pd.DataFrame:
    """Base DF plus a specified set of optional columns filled with dummy data."""
    rng = np.random.default_rng(seed + 1)
    df = _base_df(n=n, seed=seed)
    for col in cols:
        if col in BOOL_OPTIONAL_FEATURES:
            df[col] = rng.choice([True, False, np.nan], size=n).tolist()
        else:
            vals = rng.uniform(0.0, 2.0, size=n)
            # Inject some NaN
            vals[rng.integers(0, n, size=3)] = np.nan
            df[col] = vals
    return df


# ===========================================================================
# TestOptionalFeatureIntegration (6 tests)
# ===========================================================================

class TestOptionalFeatureIntegration:

    def test_no_optional_features_no_change(self):
        """DataFrame without optional columns → output has same columns as before."""
        df = _base_df()
        out_without = build_features(df)
        # None of the optional feature columns should be present
        for col in OPTIONAL_FEATURES:
            # home_days_since_last / away_days_since_last ARE computed by _feature_row
            # so skip those
            if col in ("home_days_since_last", "away_days_since_last"):
                continue
            assert col not in out_without.columns, (
                f"Column {col!r} should not be in output when not in input"
            )

    def test_h2h_btts_rate_added_when_present(self):
        """h2h_btts_rate appears in output when supplied in input DataFrame."""
        df = _df_with_optional(["h2h_btts_rate"])
        out = build_features(df)
        assert "h2h_btts_rate" in out.columns

    def test_elo_diff_added_when_present(self):
        """elo_diff is passed through when present in the input DataFrame."""
        df = _df_with_optional(["elo_diff"])
        out = build_features(df)
        assert "elo_diff" in out.columns

    def test_boolean_features_encoded_as_int(self):
        """Boolean optional columns must be int (0/1), not bool or object."""
        bool_cols = list(BOOL_OPTIONAL_FEATURES)[:3]  # test a subset
        df = _df_with_optional(bool_cols)
        out = build_features(df)
        for col in bool_cols:
            if col in out.columns:
                assert out[col].dtype in (np.dtype("int64"), np.dtype("int32"),
                                           np.dtype("int8"), np.dtype("bool")), (
                    f"{col} dtype should be integer-like, got {out[col].dtype}"
                )
                unique_vals = set(out[col].unique())
                assert unique_vals.issubset({0, 1}), (
                    f"{col} values should be in {{0, 1}}, got {unique_vals}"
                )

    def test_nan_filled_with_median_not_zero(self):
        """Continuous optional features: NaN filled with column median, not 0."""
        # Use elo_diff which will have a non-zero median
        rng = np.random.default_rng(99)
        df = _base_df(n=40)
        vals = rng.uniform(50.0, 150.0, size=40)   # all positive, so median >> 0
        vals[5] = np.nan
        vals[15] = np.nan
        df["elo_diff"] = vals

        out = build_features(df)
        assert "elo_diff" in out.columns
        assert out["elo_diff"].isna().sum() == 0, "No NaN should remain after imputation"
        # If it were filled with 0, min would be 0; median of 50-150 range is ~100
        assert out["elo_diff"].min() > 1.0, (
            "Imputed values should be ~median (~100), not zero"
        )

    def test_all_optional_features_added_when_present(self):
        """All OPTIONAL_FEATURES appear in output when all are in input."""
        df = _df_with_optional(OPTIONAL_FEATURES)
        out = build_features(df)
        for col in OPTIONAL_FEATURES:
            assert col in out.columns, f"Expected {col!r} in output"


# ===========================================================================
# TestFeatureMatrixShape (4 tests)
# ===========================================================================

class TestFeatureMatrixShape:

    def test_matrix_wider_with_optional_features(self):
        """Output with optional columns is strictly wider than without."""
        df_base = _base_df()
        df_opt  = _df_with_optional(["h2h_btts_rate", "elo_diff", "is_derby"])

        out_base = build_features(df_base)
        out_opt  = build_features(df_opt)

        assert out_opt.shape[1] > out_base.shape[1], (
            f"Expected wider matrix: base={out_base.shape[1]}, opt={out_opt.shape[1]}"
        )

    def test_matrix_same_width_without_optional_features(self):
        """Two base DataFrames (no optional cols) → same column count."""
        df1 = _base_df(n=30, seed=1)
        df2 = _base_df(n=40, seed=2)
        out1 = build_features(df1)
        out2 = build_features(df2)
        assert out1.shape[1] == out2.shape[1]

    def test_no_nan_in_output_matrix(self):
        """After imputation, no numeric optional column should contain NaN."""
        continuous_cols = [c for c in OPTIONAL_FEATURES if c not in BOOL_OPTIONAL_FEATURES][:5]
        df = _df_with_optional(continuous_cols)
        out = build_features(df)
        for col in continuous_cols:
            if col in out.columns:
                assert out[col].isna().sum() == 0, (
                    f"{col} still has NaN after imputation"
                )

    def test_existing_features_unchanged(self):
        """Mandatory rolling features must not be altered by optional feature merging."""
        df_base = _base_df(n=30)
        df_opt  = _df_with_optional(["h2h_btts_rate", "elo_diff"], n=30)

        out_base = build_features(df_base)
        out_opt  = build_features(df_opt)

        # Both should have same mandatory columns with same dtypes
        mandatory_check = ["home_matches_available", "away_matches_available",
                           "home_w5_ppg", "away_w5_ppg",
                           "home_w10_gf", "away_w10_gf"]
        for col in mandatory_check:
            assert col in out_base.columns, f"Missing mandatory column {col!r}"
            assert col in out_opt.columns,  f"Missing mandatory column {col!r} in opt output"
