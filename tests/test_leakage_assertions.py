# -*- coding: utf-8 -*-
"""Tests for leakage assertions, Wilson CIs, and profiles version manifest.

Covers:
1. _assert_no_leakage — same-date contamination raises AssertionError
2. _assert_no_leakage — rolling-feature cutoff: clean prior_df passes
3. _assert_no_leakage — future-date row raises AssertionError
4. _assert_no_leakage — empty prior_df never raises
5. run_replay in diagnostic_replay mode — no assertion fired on valid data
6. _wilson_ci — known boundary values
7. _wilson_ci — n=0 edge case
8. _wilson_ci — all hits (p=1) and zero hits (p=0)
9. _wilson_ci — CI contains the point estimate
10. _wilson_ci — wider CI for small samples than large samples
11. league_market_profiles_version.json — file exists and has required keys
12. league_market_profiles_version.json — stored SHA-256 matches actual file
13. league_market_profiles_version.json — version follows major.minor.patch
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS_DIR = ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from run_season_replay_audit import _assert_no_leakage, run_replay  # noqa: E402
from evaluate_daily_recommendations import _wilson_ci  # noqa: E402

_VERSION_FILE = ROOT / "config" / "league_market_profiles_version.json"
_PROFILES_FILE = ROOT / "src" / "football_prediction_v19" / "diagnostics" / "league_market_profiles.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_prior_df(dates: list[str]) -> pd.DataFrame:
    """Build a minimal prior_df with only a 'date' column."""
    return pd.DataFrame({"date": pd.to_datetime(dates)})


def _minimal_replay_df(n_prior: int = 60, cutoff: str = "2024-03-15") -> pd.DataFrame:
    """Build a minimal DataFrame accepted by run_replay (diagnostic_replay mode).

    Generates n_prior rows before *cutoff* and one row on *cutoff* as the
    'current matchday'.  All values are synthetic but structurally valid.
    """
    rows = []
    base = pd.Timestamp("2024-01-01")
    for i in range(n_prior):
        dt = base + pd.Timedelta(days=i)
        rows.append({
            "date":       dt,
            "home_team":  "TeamA",
            "away_team":  "TeamB",
            "home_goals": 1,
            "away_goals": 1,
            "odds_home":  2.0,
            "odds_draw":  3.4,
            "odds_away":  3.5,
        })
    # One current-matchday row
    rows.append({
        "date":       pd.Timestamp(cutoff),
        "home_team":  "TeamC",
        "away_team":  "TeamD",
        "home_goals": 2,
        "away_goals": 0,
        "odds_home":  1.9,
        "odds_draw":  3.5,
        "odds_away":  4.0,
    })
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# 1–4: _assert_no_leakage
# ---------------------------------------------------------------------------

class TestAssertNoLeakage:
    def test_same_date_contamination_raises(self):
        """A row with date == cutoff_date must trigger AssertionError."""
        cutoff = pd.Timestamp("2024-03-15")
        prior = _make_prior_df(["2024-03-14", "2024-03-15"])  # same-date contamination
        with pytest.raises(AssertionError, match="Leakage"):
            _assert_no_leakage(prior, cutoff, label="test")

    def test_future_date_raises(self):
        """A row with date > cutoff_date must trigger AssertionError."""
        cutoff = pd.Timestamp("2024-03-15")
        prior = _make_prior_df(["2024-03-13", "2024-03-16"])  # future date
        with pytest.raises(AssertionError, match="Leakage"):
            _assert_no_leakage(prior, cutoff, label="test")

    def test_rolling_feature_cutoff_clean(self):
        """All dates strictly before cutoff must not raise."""
        cutoff = pd.Timestamp("2024-03-15")
        prior = _make_prior_df(["2024-03-13", "2024-03-14"])
        _assert_no_leakage(prior, cutoff)  # must not raise

    def test_empty_prior_never_raises(self):
        """Empty prior_df is a valid early-season state — must not raise."""
        cutoff = pd.Timestamp("2024-01-01")
        prior = pd.DataFrame({"date": pd.Series([], dtype="datetime64[ns]")})
        _assert_no_leakage(prior, cutoff)  # must not raise

    def test_label_appears_in_error_message(self):
        """The label string must appear in the AssertionError message."""
        cutoff = pd.Timestamp("2024-03-15")
        prior = _make_prior_df(["2024-03-15"])
        with pytest.raises(AssertionError, match="my_label"):
            _assert_no_leakage(prior, cutoff, label="my_label")

    def test_single_clean_row_passes(self):
        """Exactly one prior row one day before cutoff must not raise."""
        cutoff = pd.Timestamp("2024-03-15")
        prior = _make_prior_df(["2024-03-14"])
        _assert_no_leakage(prior, cutoff)  # must not raise

    def test_max_date_one_second_before_cutoff(self):
        """Sub-day precision: Timestamp just before midnight of cutoff must pass."""
        cutoff = pd.Timestamp("2024-03-15")
        # Timestamp at 23:59:59 on the day before cutoff
        prior = pd.DataFrame({"date": [pd.Timestamp("2024-03-14 23:59:59")]})
        _assert_no_leakage(prior, cutoff)  # must not raise


# ---------------------------------------------------------------------------
# 5: run_replay integration — no assertion fired on valid data
# ---------------------------------------------------------------------------

class TestRunReplayNoLeakageFired:
    def test_diagnostic_replay_no_assertion(self):
        """run_replay (diagnostic_replay) must not raise AssertionError on valid data."""
        df = _minimal_replay_df(n_prior=60)
        # Should complete without error
        pred_df, eval_df = run_replay(
            df=df,
            mode="diagnostic_replay",
            min_warmup=5,
            league_name="EPL",
        )
        assert len(pred_df) >= 1
        assert len(eval_df) >= 1

    def test_prior_df_never_contains_cutoff_date(self):
        """Verify directly that run_replay prior_df rows are always < cutoff.

        We test this indirectly: if any prior_df contained a match on the
        current matchday, _assert_no_leakage would have fired.  Since run_replay
        completes without error, the filter is correct.
        """
        df = _minimal_replay_df(n_prior=60)
        pred_df, _eval_df = run_replay(
            df=df,
            mode="diagnostic_replay",
            min_warmup=5,
            league_name="EPL",
        )
        # The last row in pred_df corresponds to the current-matchday match;
        # its date must be >= all dates in any prior_df used to build it.
        assert not pred_df.empty


# ---------------------------------------------------------------------------
# 6–10: _wilson_ci
# ---------------------------------------------------------------------------

class TestWilsonCI:
    def test_n_zero_returns_full_interval(self):
        lo, hi = _wilson_ci(0, 0)
        assert lo == 0.0
        assert hi == 1.0

    def test_all_hits_hi_close_to_one(self):
        """p=1 → upper bound clipped to 1.0 (or very close), lower bound < 1.0."""
        lo, hi = _wilson_ci(100, 100)
        assert math.isclose(hi, 1.0, abs_tol=1e-9), f"hi={hi}"
        assert lo < 1.0

    def test_zero_hits_lo_close_to_zero(self):
        """p=0 → lower bound 0.0, upper bound > 0.0."""
        lo, hi = _wilson_ci(100, 0)
        assert lo == 0.0
        assert hi > 0.0

    def test_ci_contains_point_estimate(self):
        """The CI must always contain the observed proportion."""
        for n, hits in [(10, 5), (50, 30), (200, 160), (5, 1)]:
            p_hat = hits / n
            lo, hi = _wilson_ci(n, hits)
            assert lo <= p_hat <= hi, (
                f"CI [{lo:.4f}, {hi:.4f}] does not contain p_hat={p_hat:.4f} "
                f"for n={n}, hits={hits}"
            )

    def test_larger_sample_narrower_ci(self):
        """Larger n → narrower CI for the same observed proportion."""
        lo_small, hi_small = _wilson_ci(10, 5)
        lo_large, hi_large = _wilson_ci(1000, 500)
        width_small = hi_small - lo_small
        width_large = hi_large - lo_large
        assert width_large < width_small

    def test_symmetric_around_half(self):
        """For p=0.5 the Wilson CI should be symmetric around 0.5."""
        lo, hi = _wilson_ci(100, 50)
        mid = (lo + hi) / 2
        assert abs(mid - 0.5) < 0.01  # allow small floating-point drift

    def test_bounds_clipped_to_unit_interval(self):
        """Bounds must always be in [0, 1]."""
        for n, hits in [(1, 0), (1, 1), (2, 0), (2, 2), (3, 1)]:
            lo, hi = _wilson_ci(n, hits)
            assert 0.0 <= lo <= 1.0
            assert 0.0 <= hi <= 1.0

    def test_known_value_approx(self):
        """Cross-check against a hand-computed Wilson CI for n=100, hits=70.

        p̂ = 0.70, z=1.96:
        Using the Wilson formula the expected CI is approximately [0.601, 0.783].
        """
        lo, hi = _wilson_ci(100, 70)
        assert abs(lo - 0.601) < 0.005, f"lo={lo:.4f}"
        assert abs(hi - 0.783) < 0.005, f"hi={hi:.4f}"

    def test_n_hits_not_float_coerced(self):
        """Function should handle integer inputs without error."""
        lo, hi = _wilson_ci(50, 25)
        assert isinstance(lo, float)
        assert isinstance(hi, float)


# ---------------------------------------------------------------------------
# 11–13: league_market_profiles_version.json
# ---------------------------------------------------------------------------

class TestProfilesVersion:
    def test_version_file_exists(self):
        assert _VERSION_FILE.exists(), (
            f"Missing: {_VERSION_FILE}\n"
            "Run: python scripts/update_profiles_version.py  (or create manually)"
        )

    def test_required_keys_present(self):
        data = json.loads(_VERSION_FILE.read_text(encoding="utf-8"))
        required = {"version", "last_updated", "profiles_file", "profiles_sha256"}
        missing = required - data.keys()
        assert not missing, f"Missing keys in version file: {missing}"

    def test_version_follows_semver(self):
        data = json.loads(_VERSION_FILE.read_text(encoding="utf-8"))
        version = data["version"]
        parts = version.split(".")
        assert len(parts) == 3, f"version must be major.minor.patch, got: {version!r}"
        for part in parts:
            assert part.isdigit(), f"Each part must be numeric, got {part!r} in {version!r}"

    def test_stored_sha256_matches_actual_file(self):
        """Detect untracked changes to league_market_profiles.py.

        If this test fails, the profiles file was modified without updating
        config/league_market_profiles_version.json.  Update the version file
        to reflect the new hash and bump the version number.
        """
        assert _PROFILES_FILE.exists(), f"Profiles file not found: {_PROFILES_FILE}"
        actual_hash = hashlib.sha256(_PROFILES_FILE.read_bytes()).hexdigest()
        data = json.loads(_VERSION_FILE.read_text(encoding="utf-8"))
        stored_hash = data["profiles_sha256"]
        assert actual_hash == stored_hash, (
            f"league_market_profiles.py has changed but "
            f"config/league_market_profiles_version.json was not updated.\n"
            f"Stored SHA-256 : {stored_hash}\n"
            f"Actual SHA-256 : {actual_hash}\n"
            "Update 'profiles_sha256' and bump 'version' in the JSON file."
        )

    def test_profiles_file_path_is_correct(self):
        """The profiles_file path recorded in the JSON must resolve to an existing file."""
        data = json.loads(_VERSION_FILE.read_text(encoding="utf-8"))
        recorded_path = ROOT / data["profiles_file"]
        assert recorded_path.exists(), (
            f"profiles_file path in version JSON does not exist: {recorded_path}"
        )

    def test_schema_version_is_integer(self):
        data = json.loads(_VERSION_FILE.read_text(encoding="utf-8"))
        if "schema_version" in data:
            assert isinstance(data["schema_version"], int)
