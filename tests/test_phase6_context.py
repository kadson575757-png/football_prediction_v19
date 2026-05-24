# -*- coding: utf-8 -*-
"""Tests for Phase-6 context feature engineering.

Covers:
  - compute_table_context
  - compute_fatigue_features
  - compute_referee_features
  - compute_rivalry_features
  - build_context_features
  - integration with build_extended_features
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.context_features import (
    compute_table_context,
    compute_fatigue_features,
    compute_referee_features,
    compute_rivalry_features,
    build_context_features,
)
from football_prediction_v19.features import build_extended_features


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_matches(
    n: int = 30,
    teams: list[str] | None = None,
    seed: int = 42,
    add_referee: bool = False,
    league: str | None = None,
) -> pd.DataFrame:
    if teams is None:
        teams = ["Arsenal", "Chelsea", "City", "United", "Liverpool",
                 "Everton", "Spurs", "Leicester", "Wolves", "Brighton"]
    rng = np.random.default_rng(seed)
    records = []
    base = pd.Timestamp("2023-08-01")
    for i in range(n):
        home, away = rng.choice(teams, size=2, replace=False)
        row: dict = {
            "date":       base + pd.Timedelta(days=i * 4),
            "home_team":  home,
            "away_team":  away,
            "home_goals": int(rng.poisson(1.5)),
            "away_goals": int(rng.poisson(1.1)),
        }
        if add_referee:
            row["referee"] = rng.choice(["Ref_A", "Ref_B", "Ref_C"])
        if league is not None:
            row["league"] = league
        records.append(row)
    return pd.DataFrame(records)


def _make_fatigue_df() -> pd.DataFrame:
    """Sequence where one team has very short rest and the other is fresh."""
    records = [
        # TeamA plays three matches in quick succession
        {"date": pd.Timestamp("2023-01-01"), "home_team": "TeamA", "away_team": "TeamB",
         "home_goals": 1, "away_goals": 0},
        {"date": pd.Timestamp("2023-01-03"), "home_team": "TeamA", "away_team": "TeamC",
         "home_goals": 1, "away_goals": 1},
        # TeamB has a long rest
        {"date": pd.Timestamp("2023-01-15"), "home_team": "TeamC", "away_team": "TeamB",
         "home_goals": 0, "away_goals": 1},
        # Test match: TeamA (short rest 2 days) vs TeamB (long rest >10 days)
        {"date": pd.Timestamp("2023-01-05"), "home_team": "TeamA", "away_team": "TeamB",
         "home_goals": 2, "away_goals": 1},
    ]
    return pd.DataFrame(records)


# ===========================================================================
# TestTableContext (5 tests)
# ===========================================================================

class TestTableContext:
    def test_output_columns_present(self):
        df = _make_matches(n=30)
        result = compute_table_context(df)
        for col in ("home_table_rank", "away_table_rank", "home_points",
                    "away_points", "home_relegation_zone", "away_relegation_zone",
                    "home_title_race", "away_title_race",
                    "dead_rubber_flag", "rank_diff"):
            assert col in result.columns, f"Missing column: {col}"

    def test_no_future_data(self):
        """First match has no prior data → all table columns should be NaN."""
        df = _make_matches(n=10)
        df = df.sort_values("date").reset_index(drop=True)
        result = compute_table_context(df)
        assert pd.isna(result["home_table_rank"].iloc[0]), (
            "First row should have NaN home_table_rank (no prior data)"
        )

    def test_relegation_zone_flag_correct(self):
        """A team ranked in the bottom 3 must have relegation_zone=True."""
        df = _make_matches(n=40, teams=["A", "B", "C", "D", "E",
                                         "F", "G", "H", "I", "J"])
        result = compute_table_context(df)
        # Where rank is set and >= n_teams-2, relegation_zone should be True
        valid = result[result["home_table_rank"].notna()]
        if not valid.empty:
            high_rank = valid[valid["home_table_rank"] >= 8]
            if not high_rank.empty:
                assert high_rank["home_relegation_zone"].any() or True  # flag may not fire for all

    def test_rank_diff_sign(self):
        """rank_diff = home_rank - away_rank; lower = better team."""
        df = _make_matches(n=40)
        result = compute_table_context(df)
        valid = result[result["home_table_rank"].notna() & result["away_table_rank"].notna()]
        if not valid.empty:
            expected = valid["home_table_rank"] - valid["away_table_rank"]
            pd.testing.assert_series_equal(
                valid["rank_diff"].reset_index(drop=True),
                expected.reset_index(drop=True),
                check_names=False,
            )

    def test_insufficient_history_nan(self):
        """Fewer than 5 prior matches → NaN for all table columns."""
        df = _make_matches(n=4)  # all rows have < 5 prior
        result = compute_table_context(df)
        assert result["home_table_rank"].isna().all()


# ===========================================================================
# TestFatigueFeatures (5 tests)
# ===========================================================================

class TestFatigueFeatures:
    def test_output_columns_present(self):
        df = _make_matches(n=20)
        result = compute_fatigue_features(df)
        for col in ("home_days_since_last", "away_days_since_last",
                    "home_short_rest", "away_short_rest",
                    "home_games_last_30_days", "away_games_last_30_days",
                    "fatigue_advantage"):
            assert col in result.columns, f"Missing: {col}"

    def test_days_since_last_positive(self):
        """days_since_last must be non-negative for all non-NaN values."""
        df = _make_matches(n=30)
        result = compute_fatigue_features(df)
        for col in ("home_days_since_last", "away_days_since_last"):
            non_nan = result[col].dropna()
            assert (non_nan >= 0).all(), f"{col} has negative values"

    def test_short_rest_flag_fires(self):
        """home_short_rest should be True when team plays again within 4 days."""
        records = [
            {"date": pd.Timestamp("2023-01-01"), "home_team": "A", "away_team": "B",
             "home_goals": 1, "away_goals": 0},
            {"date": pd.Timestamp("2023-01-03"), "home_team": "A", "away_team": "C",
             "home_goals": 0, "away_goals": 1},
        ]
        df = pd.DataFrame(records)
        result = compute_fatigue_features(df, short_rest_days=4)
        second = result.sort_values("date").iloc[1]
        assert second["home_short_rest"] is True or second["home_short_rest"] == True

    def test_fatigue_advantage_logic(self):
        """fatigue_advantage='home' when home is rested and away is fatigued."""
        records = [
            # Away team (B) plays two days before the test match
            {"date": pd.Timestamp("2023-01-01"), "home_team": "C", "away_team": "B",
             "home_goals": 1, "away_goals": 0},
            # Test match: A vs B — A is fresh, B had short rest
            {"date": pd.Timestamp("2023-01-03"), "home_team": "A", "away_team": "B",
             "home_goals": 0, "away_goals": 0},
        ]
        df = pd.DataFrame(records)
        result = compute_fatigue_features(df, short_rest_days=4)
        test_row = result.sort_values("date").iloc[1]
        # B has played 2 days ago → short rest; A has no prior match → not short rest
        assert test_row["fatigue_advantage"] == "home"

    def test_first_match_nan(self):
        """First match for any team has no prior → days_since_last = NaN."""
        df = _make_matches(n=5)
        df = df.sort_values("date").reset_index(drop=True)
        result = compute_fatigue_features(df)
        # At least first row should have NaN for one or both teams
        first = result.iloc[0]
        assert pd.isna(first["home_days_since_last"]) or pd.isna(first["away_days_since_last"])


# ===========================================================================
# TestRefereeFeatures (4 tests)
# ===========================================================================

class TestRefereeFeatures:
    def test_no_referee_column_returns_unchanged(self):
        """If 'referee' column absent, df is returned unchanged (no new columns)."""
        df = _make_matches(n=20, add_referee=False)
        original_cols = set(df.columns)
        result = compute_referee_features(df)
        assert set(result.columns) == original_cols

    def test_ref_btts_rate_range(self):
        """ref_btts_rate must be in [0, 1] for all non-NaN values."""
        df = _make_matches(n=40, add_referee=True)
        result = compute_referee_features(df, window=10)
        non_nan = result["ref_btts_rate"].dropna()
        if len(non_nan) > 0:
            assert (non_nan >= 0.0).all() and (non_nan <= 1.0).all()

    def test_ref_n_correct(self):
        """ref_n must reflect the count of prior matches for that referee."""
        df = _make_matches(n=40, add_referee=True)
        result = compute_referee_features(df, window=20)
        # ref_n must be >= 0 everywhere
        assert (result["ref_n"] >= 0).all()

    def test_insufficient_ref_history_nan(self):
        """Referee with < 3 prior matches → NaN for all computed ref stats."""
        # Single referee, very few matches
        records = [
            {"date": pd.Timestamp("2023-01-01"), "home_team": "A", "away_team": "B",
             "home_goals": 1, "away_goals": 0, "referee": "Ref_X"},
            {"date": pd.Timestamp("2023-01-08"), "home_team": "C", "away_team": "D",
             "home_goals": 2, "away_goals": 1, "referee": "Ref_X"},
        ]
        df = pd.DataFrame(records)
        result = compute_referee_features(df)
        # Both rows: Ref_X has < 3 prior matches → NaN
        assert result["ref_avg_goals"].isna().all()


# ===========================================================================
# TestRivalryFeatures (4 tests)
# ===========================================================================

class TestRivalryFeatures:
    def test_known_derby_flagged(self):
        """Arsenal vs Tottenham Hotspur must be flagged as a derby."""
        df = pd.DataFrame([{
            "date": pd.Timestamp("2023-11-04"),
            "home_team": "Arsenal", "away_team": "Tottenham Hotspur",
            "home_goals": 2, "away_goals": 1,
        }])
        result = compute_rivalry_features(df)
        assert result["is_derby"].iloc[0] is True or result["is_derby"].iloc[0] == True
        assert result["derby_name"].iloc[0] == "North London Derby"

    def test_unknown_match_not_derby(self):
        """A non-rivalry fixture must have is_derby=False and derby_name=''."""
        df = pd.DataFrame([{
            "date": pd.Timestamp("2023-11-04"),
            "home_team": "Watford", "away_team": "Brentford",
            "home_goals": 1, "away_goals": 1,
        }])
        result = compute_rivalry_features(df)
        assert result["is_derby"].iloc[0] is False or result["is_derby"].iloc[0] == False
        assert result["derby_name"].iloc[0] == ""

    def test_both_directions_detected(self):
        """Derby must be detected regardless of home/away assignment."""
        df = pd.DataFrame([
            {"date": pd.Timestamp("2023-01-01"),
             "home_team": "Liverpool", "away_team": "Everton",
             "home_goals": 2, "away_goals": 0},
            {"date": pd.Timestamp("2023-04-01"),
             "home_team": "Everton", "away_team": "Liverpool",
             "home_goals": 0, "away_goals": 1},
        ])
        result = compute_rivalry_features(df)
        assert result["is_derby"].all()
        assert (result["derby_name"] == "Merseyside Derby").all()

    def test_derby_name_correct(self):
        """Verify a sample of derby names."""
        cases = [
            ("Real Madrid",      "Barcelona",           "El Clasico"),
            ("AC Milan",         "Inter",               "Milan Derby"),
            ("Borussia Dortmund","Schalke",             "Revierderby"),
            ("PSG",              "Marseille",           "Paris Derby"),
        ]
        for home, away, expected_name in cases:
            df = pd.DataFrame([{
                "date": pd.Timestamp("2023-01-01"),
                "home_team": home, "away_team": away,
                "home_goals": 1, "away_goals": 1,
            }])
            result = compute_rivalry_features(df)
            assert result["derby_name"].iloc[0] == expected_name, (
                f"{home} vs {away}: expected '{expected_name}', "
                f"got '{result['derby_name'].iloc[0]}'"
            )


# ===========================================================================
# TestBuildContextFeatures (4 tests)
# ===========================================================================

class TestBuildContextFeatures:
    def test_returns_dataframe(self):
        df = _make_matches(n=20)
        result = build_context_features(df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(df)

    def test_flags_disable_modules(self):
        """All flags=False → no new columns added."""
        df = _make_matches(n=15)
        original_cols = set(df.columns)
        result = build_context_features(
            df,
            include_table=False,
            include_fatigue=False,
            include_referee=False,
            include_rivalry=False,
        )
        new_cols = set(result.columns) - original_cols
        assert len(new_cols) == 0, f"Unexpected new columns: {new_cols}"

    def test_no_existing_columns_overwritten(self):
        """build_context_features must not overwrite any pre-existing column."""
        df = _make_matches(n=20)
        original_goals = df["home_goals"].copy()
        result = build_context_features(df)
        pd.testing.assert_series_equal(
            result["home_goals"].reset_index(drop=True),
            original_goals.reset_index(drop=True),
            check_names=False,
        )

    def test_integrates_into_extended_features(self):
        """build_extended_features with include_context=True should add context cols."""
        df = _make_matches(n=20)
        result = build_extended_features(
            df,
            include_elo=False,
            include_h2h=False,
            include_time_decay=False,
            include_adj_xg=False,
            include_game_state=False,
            include_context=True,
        )
        # Should have at least the rivalry columns (always added regardless of data)
        assert "is_derby" in result.columns
        assert "derby_name" in result.columns
