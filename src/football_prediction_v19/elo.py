# -*- coding: utf-8 -*-
"""Elo rating system for football teams.

DIAGNOSTIC / ANALYTICAL LAYER ONLY.
- No betting, ROI, or staking logic.
- Runs prior to match for each row (no leakage).

Public API
----------
EloRatingSystem
"""
from __future__ import annotations

import pandas as pd

__all__ = ["EloRatingSystem"]


class EloRatingSystem:
    """Standard Elo rating with home-advantage offset.

    Parameters
    ----------
    k:
        K-factor (learning rate).  Default 32.
    home_advantage:
        Elo points added to the home team's effective rating.  Default 100.
    initial_rating:
        Starting Elo for any new team.  Default 1500.
    """

    def __init__(
        self,
        k: float = 32.0,
        home_advantage: float = 100.0,
        initial_rating: float = 1500.0,
    ) -> None:
        self.k = k
        self.home_advantage = home_advantage
        self.initial_rating = initial_rating
        self._ratings: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, team: str) -> float:
        return self._ratings.get(team, self.initial_rating)

    def _expected(self, rating_a: float, rating_b: float) -> float:
        """Logistic expected score for player A versus player B."""
        return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(
        self,
        home_team: str,
        away_team: str,
        home_goals: int,
        away_goals: int,
    ) -> None:
        """Update ratings after a completed match.

        Parameters
        ----------
        home_team, away_team:
            Team names.
        home_goals, away_goals:
            Final score.
        """
        hr = self._get(home_team)
        ar = self._get(away_team)

        # Home team gets home_advantage added to its effective rating
        expected_home = self._expected(hr + self.home_advantage, ar)

        if home_goals > away_goals:
            actual_home = 1.0
        elif home_goals == away_goals:
            actual_home = 0.5
        else:
            actual_home = 0.0

        delta = self.k * (actual_home - expected_home)
        self._ratings[home_team] = hr + delta
        self._ratings[away_team] = ar - delta

    def get_ratings_before_match(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add pre-match Elo ratings to each row, updating after each match.

        Processes matches chronologically.  The rating snapshot captured for
        each row is the Elo **before** that match is played (no leakage).

        New columns added:
            ``elo_home``, ``elo_away``, ``elo_diff`` (home - away).

        Parameters
        ----------
        df:
            DataFrame with columns: date, home_team, away_team,
            home_goals, away_goals (sorted or unsorted).

        Returns
        -------
        pd.DataFrame (copy of *df* with new columns appended).
        """
        out = df.copy()
        out["date"] = pd.to_datetime(out["date"])
        out = out.sort_values("date").reset_index(drop=True)

        elo_home: list[float] = []
        elo_away: list[float] = []

        for _, row in out.iterrows():
            h = row["home_team"]
            a = row["away_team"]

            # Snapshot BEFORE this match
            elo_home.append(self._get(h))
            elo_away.append(self._get(a))

            # Update ratings with result
            hg = int(row["home_goals"])
            ag = int(row["away_goals"])
            self.update(h, a, hg, ag)

        out["elo_home"] = elo_home
        out["elo_away"] = elo_away
        out["elo_diff"] = out["elo_home"] - out["elo_away"]
        return out

    def get_all_ratings(self) -> dict[str, float]:
        """Return current Elo ratings for all known teams."""
        return dict(self._ratings)
