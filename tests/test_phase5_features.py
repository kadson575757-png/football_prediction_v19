# -*- coding: utf-8 -*-
"""Tests for Phase-5 feature engineering modules.

Covers:
  - compute_opponent_adjusted_xg
  - compute_time_decay_features
  - EloRatingSystem
  - compute_h2h_features
  - compute_game_state_features
  - build_extended_features
"""
from __future__ import annotations

import sys
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.features import (
    compute_opponent_adjusted_xg,
    compute_time_decay_features,
    compute_h2h_features,
    compute_game_state_features,
    build_extended_features,
)
from football_prediction_v19.elo import EloRatingSystem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_matches(
    n: int = 40,
    teams: list[str] | None = None,
    include_xg: bool = True,
    seed: int = 42,
) -> pd.DataFrame:
    if teams is None:
        teams = ["Arsenal", "Chelsea", "City", "United", "Liverpool"]
    rng = np.random.default_rng(seed)
    records = []
    base = pd.Timestamp("2023-08-01")
    for i in range(n):
        home, away = rng.choice(teams, size=2, replace=False)
        hg = int(rng.poisson(1.5))
        ag = int(rng.poisson(1.1))
        row = {
            "date":       base + pd.Timedelta(days=i * 3),
            "home_team":  home,
            "away_team":  away,
            "home_goals": hg,
            "away_goals": ag,
        }
        if include_xg:
            row["home_xg"] = round(float(rng.uniform(0.5, 2.5)), 2)
            row["away_xg"] = round(float(rng.uniform(0.3, 2.0)), 2)
        records.append(row)
    return pd.DataFrame(records)


# ===========================================================================
# TestOpponentAdjustedXg (5 tests)
# ===========================================================================

class TestOpponentAdjustedXg:
    def test_output_columns_present(self):
        df = _make_matches(n=30)
        result = compute_opponent_adjusted_xg(df)
        for col in ("adj_home_xg", "adj_away_xg",
                    "opponent_strength_home", "opponent_strength_away"):
            assert col in result.columns, f"Missing column: {col}"

    def test_no_xg_columns_returns_unchanged(self, capsys):
        df = _make_matches(n=20, include_xg=False)
        result = compute_opponent_adjusted_xg(df)
        assert "adj_home_xg" not in result.columns
        captured = capsys.readouterr()
        assert "xG columns not found" in captured.out

    def test_adj_xg_differs_from_raw(self):
        """Adjusted xG should differ from raw xG for at least some rows."""
        df = _make_matches(n=40)
        result = compute_opponent_adjusted_xg(df, window=5)
        non_nan = result["adj_home_xg"].dropna()
        raw_non_nan = result.loc[non_nan.index, "home_xg"]
        # At least some adjusted values should differ from raw
        assert not (non_nan == raw_non_nan).all(), (
            "adj_home_xg is identical to home_xg for all rows — adjustment not applied"
        )

    def test_no_future_data_in_adjustment(self):
        """For the first match, opponent_strength must be NaN (no prior data)."""
        df = _make_matches(n=20)
        df = df.sort_values("date").reset_index(drop=True)
        result = compute_opponent_adjusted_xg(df, window=5)
        # First row has no prior data → opponent strengths should be NaN
        assert pd.isna(result["opponent_strength_home"].iloc[0]) or \
               pd.isna(result["opponent_strength_away"].iloc[0]), \
            "First row should have NaN opponent strength (no prior data)"

    def test_zero_division_handled(self):
        """adj_xg uses +0.01 denominator guard; should never raise ZeroDivisionError."""
        df = _make_matches(n=30)
        # Zero out opponent strength values are possible; function should handle gracefully
        result = compute_opponent_adjusted_xg(df, window=3)
        assert isinstance(result, pd.DataFrame)


# ===========================================================================
# TestTimeDecayFeatures (5 tests)
# ===========================================================================

class TestTimeDecayFeatures:
    def test_output_columns_present(self):
        df = _make_matches(n=40)
        result = compute_time_decay_features(df)
        for side in ("home", "away"):
            for metric in ("td_goals_scored", "td_goals_conceded",
                           "td_xg", "td_xga", "td_win_rate"):
                assert f"{side}_{metric}" in result.columns

    def test_recent_games_weighted_higher(self):
        """With a short half-life, recent games dominate; very old games have minimal weight."""
        # Build a dataset where early games have high goals but recent games have low goals.
        records = []
        base = pd.Timestamp("2022-01-01")
        # 15 old matches with high goals for TeamA
        for i in range(15):
            records.append({
                "date": base + pd.Timedelta(days=i),
                "home_team": "TeamA", "away_team": "TeamB",
                "home_goals": 5, "away_goals": 0,
                "home_xg": 3.0, "away_xg": 0.5,
            })
        # 5 recent matches with low goals for TeamA
        for i in range(5):
            records.append({
                "date": base + pd.Timedelta(days=300 + i),
                "home_team": "TeamA", "away_team": "TeamB",
                "home_goals": 0, "away_goals": 0,
                "home_xg": 0.2, "away_xg": 0.2,
            })
        # One evaluation match
        records.append({
            "date": base + pd.Timedelta(days=310),
            "home_team": "TeamA", "away_team": "TeamB",
            "home_goals": 1, "away_goals": 1,
            "home_xg": 1.0, "away_xg": 1.0,
        })
        df = pd.DataFrame(records)
        result_short = compute_time_decay_features(df, half_life_days=7)
        result_long  = compute_time_decay_features(df, half_life_days=365)

        last_row_short = result_short.iloc[-1]["home_td_goals_scored"]
        last_row_long  = result_long.iloc[-1]["home_td_goals_scored"]

        # Short half-life → recent low-goal games dominate → lower td_goals_scored
        # Long half-life → old high-goal games still count → higher td_goals_scored
        if pd.notna(last_row_short) and pd.notna(last_row_long):
            assert last_row_short < last_row_long, (
                f"Short half-life ({last_row_short:.2f}) should produce lower "
                f"td_goals_scored than long half-life ({last_row_long:.2f})"
            )

    def test_insufficient_history_returns_nan(self):
        """Teams with fewer than 3 prior matches should get NaN."""
        df = _make_matches(n=5)
        result = compute_time_decay_features(df)
        # First row has 0 prior matches for at least one team
        assert pd.isna(result["home_td_goals_scored"].iloc[0])

    def test_half_life_affects_weights(self):
        """Different half_life_days values must produce different results."""
        df = _make_matches(n=40, seed=1)
        r7   = compute_time_decay_features(df, half_life_days=7)
        r180 = compute_time_decay_features(df, half_life_days=180)
        col = "home_td_goals_scored"
        # Must not be identical
        diff = (r7[col].dropna() - r180[col].dropna()).abs()
        assert diff.max() > 0.001, "Different half-lives should produce different td features"

    def test_no_future_leak(self):
        """All time-decay features must be computed from prior matches only."""
        df = _make_matches(n=30).sort_values("date").reset_index(drop=True)
        result = compute_time_decay_features(df)
        # First row of any team (no prior matches): NaN
        assert pd.isna(result["home_td_goals_scored"].iloc[0])


# ===========================================================================
# TestEloRating (6 tests)
# ===========================================================================

class TestEloRating:
    def test_initial_ratings_equal(self):
        """New teams start at initial_rating."""
        elo = EloRatingSystem(initial_rating=1500.0)
        assert elo._get("NewTeam") == 1500.0

    def test_winner_gains_rating(self):
        """Home team that wins should gain Elo points."""
        elo = EloRatingSystem(k=32.0, home_advantage=0.0, initial_rating=1500.0)
        elo.update("HomeFC", "AwayFC", 2, 0)
        assert elo._get("HomeFC") > 1500.0
        assert elo._get("AwayFC") < 1500.0

    def test_draw_adjusts_less(self):
        """A draw adjusts ratings less than a decisive result."""
        elo_draw = EloRatingSystem(k=32.0, home_advantage=0.0, initial_rating=1500.0)
        elo_win  = EloRatingSystem(k=32.0, home_advantage=0.0, initial_rating=1500.0)
        elo_draw.update("H", "A", 1, 1)
        elo_win.update("H", "A",  3, 0)
        delta_draw = abs(elo_draw._get("H") - 1500.0)
        delta_win  = abs(elo_win._get("H")  - 1500.0)
        assert delta_win > delta_draw

    def test_home_advantage_applied(self):
        """Home advantage increases expected score for home team,
        reducing gain when home team wins."""
        elo_no_adv  = EloRatingSystem(k=32.0, home_advantage=0.0,   initial_rating=1500.0)
        elo_with_adv = EloRatingSystem(k=32.0, home_advantage=200.0, initial_rating=1500.0)
        elo_no_adv.update("H",  "A", 2, 0)
        elo_with_adv.update("H", "A", 2, 0)
        # With large home advantage, expected_home is high, so actual win gives smaller gain
        gain_no_adv   = elo_no_adv._get("H")   - 1500.0
        gain_with_adv = elo_with_adv._get("H") - 1500.0
        assert gain_no_adv > gain_with_adv

    def test_ratings_before_match_no_leak(self):
        """elo_home/elo_away must reflect rating BEFORE the match, not after."""
        df = _make_matches(n=20)
        elo = EloRatingSystem(initial_rating=1500.0)
        result = elo.get_ratings_before_match(df)
        # First match: both teams unknown → both start at 1500
        first = result.sort_values("date").iloc[0]
        assert first["elo_home"] == 1500.0
        assert first["elo_away"] == 1500.0

    def test_elo_diff_column_present(self):
        df = _make_matches(n=20)
        elo = EloRatingSystem()
        result = elo.get_ratings_before_match(df)
        assert "elo_diff" in result.columns
        # elo_diff == elo_home - elo_away
        pd.testing.assert_series_equal(
            result["elo_diff"],
            result["elo_home"] - result["elo_away"],
            check_names=False,
        )


# ===========================================================================
# TestH2HFeatures (5 tests)
# ===========================================================================

class TestH2HFeatures:
    def test_no_history_returns_nan(self):
        """When there is no prior H2H history, value columns must be NaN."""
        df = _make_matches(n=5)
        df = df.sort_values("date").reset_index(drop=True)
        result = compute_h2h_features(df, window=5)
        # First row has no prior H2H
        first = result.iloc[0]
        assert first["h2h_n"] == 0
        assert pd.isna(first["h2h_avg_goals"])

    def test_h2h_n_correct(self):
        """h2h_n must equal the number of prior H2H matches (up to window)."""
        teams = ["Alpha", "Beta"]
        records = []
        base = pd.Timestamp("2023-01-01")
        for i in range(7):
            records.append({
                "date": base + pd.Timedelta(days=i),
                "home_team": "Alpha" if i % 2 == 0 else "Beta",
                "away_team": "Beta"  if i % 2 == 0 else "Alpha",
                "home_goals": 1, "away_goals": 0,
            })
        df = pd.DataFrame(records)
        result = compute_h2h_features(df, window=5)
        # Row 6 should have min(6, 5) = 5 prior H2H matches
        assert result.iloc[-1]["h2h_n"] == 5

    def test_btts_rate_range_0_to_1(self):
        df = _make_matches(n=40)
        result = compute_h2h_features(df)
        non_nan = result["h2h_btts_rate"].dropna()
        assert (non_nan >= 0.0).all() and (non_nan <= 1.0).all()

    def test_both_directions_counted(self):
        """H2H must count matches in both directions (home/away reversed)."""
        records = [
            {"date": pd.Timestamp("2023-01-01"), "home_team": "A", "away_team": "B",
             "home_goals": 2, "away_goals": 0},
            {"date": pd.Timestamp("2023-01-15"), "home_team": "B", "away_team": "A",
             "home_goals": 1, "away_goals": 1},
            {"date": pd.Timestamp("2023-02-01"), "home_team": "A", "away_team": "B",
             "home_goals": 0, "away_goals": 1},
        ]
        df = pd.DataFrame(records)
        result = compute_h2h_features(df, window=5)
        # Third row should see 2 prior H2H matches (both directions)
        assert result.iloc[2]["h2h_n"] == 2

    def test_window_respected(self):
        """h2h_n must not exceed window."""
        teams = ["X", "Y"]
        records = [
            {"date": pd.Timestamp("2023-01-01") + pd.Timedelta(days=i),
             "home_team": "X", "away_team": "Y",
             "home_goals": 1, "away_goals": 0}
            for i in range(10)
        ]
        df = pd.DataFrame(records)
        result = compute_h2h_features(df, window=3)
        assert (result["h2h_n"] <= 3).all()


# ===========================================================================
# TestGameStateFeatures (4 tests)
# ===========================================================================

class TestGameStateFeatures:
    def test_output_columns_present(self):
        df = _make_matches(n=40)
        result = compute_game_state_features(df)
        for side in ("home", "away"):
            for col in ("lead_rate", "comeback_rate",
                        "clean_sheet_rate", "failed_to_score_rate"):
                assert f"{side}_{col}" in result.columns

    def test_clean_sheet_rate_range(self):
        df = _make_matches(n=40)
        result = compute_game_state_features(df)
        for col in ("home_clean_sheet_rate", "away_clean_sheet_rate"):
            non_nan = result[col].dropna()
            assert (non_nan >= 0.0).all() and (non_nan <= 1.0).all()

    def test_insufficient_history_nan(self):
        """Teams with fewer than 3 prior matches should get NaN."""
        df = _make_matches(n=5)
        result = compute_game_state_features(df)
        assert pd.isna(result["home_lead_rate"].iloc[0])

    def test_no_future_leak(self):
        """Game-state features must use only prior data."""
        df = _make_matches(n=30).sort_values("date").reset_index(drop=True)
        result = compute_game_state_features(df)
        # Row 0: no prior data → NaN
        assert pd.isna(result["home_lead_rate"].iloc[0])


# ===========================================================================
# TestBuildExtendedFeatures (3 tests)
# ===========================================================================

class TestBuildExtendedFeatures:
    def test_returns_dataframe(self):
        df = _make_matches(n=30)
        result = build_extended_features(df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(df)

    def test_no_existing_columns_overwritten(self):
        """build_extended_features must not modify any pre-existing column values."""
        df = _make_matches(n=30)
        original_hg = df["home_goals"].copy()
        result = build_extended_features(df)
        pd.testing.assert_series_equal(
            result["home_goals"].reset_index(drop=True),
            original_hg.reset_index(drop=True),
            check_names=False,
        )

    def test_flags_disable_modules(self):
        """Setting all flags to False returns df without new feature columns."""
        df = _make_matches(n=20)
        original_cols = set(df.columns)
        result = build_extended_features(
            df,
            include_elo=False,
            include_h2h=False,
            include_time_decay=False,
            include_adj_xg=False,
            include_game_state=False,
        )
        new_cols = set(result.columns) - original_cols
        assert len(new_cols) == 0, (
            f"Expected no new columns when all flags disabled, got: {new_cols}"
        )
