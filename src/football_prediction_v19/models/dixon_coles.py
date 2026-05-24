# -*- coding: utf-8 -*-
"""Dixon-Coles Poisson football match probability model.

DIAGNOSTIC / ANALYTICAL LAYER ONLY.
- Runs in parallel with the existing ML classifier.
- Does not replace or modify the existing model or its predictions.
- No betting, ROI, or staking logic.

Reference:
    Dixon, M. J. & Coles, S. G. (1997).
    Modelling Association Football Scores and Inefficiencies in the
    Football Betting Market.  Applied Statistics, 46(2), 265-280.

Public API
----------
DixonColesModel
    Bivariate Poisson model with low-score correlation correction.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import poisson

__all__ = ["DixonColesModel"]


class DixonColesModel:
    """Bivariate Poisson model with Dixon-Coles low-score correction.

    Parameters
    ----------
    rho:
        Low-score dependency parameter (typically small negative).
        Default -0.13 (from the original paper).
    max_goals:
        Maximum goals per team for the score matrix (0 … max_goals inclusive).
        Default 8.
    """

    def __init__(self, rho: float = -0.13, max_goals: int = 8) -> None:
        self.rho = rho
        self.max_goals = max_goals
        self.attack: dict[str, float] = {}
        self.defense: dict[str, float] = {}
        self.home_adv: float = 0.0
        self.fitted: bool = False

    # ------------------------------------------------------------------
    # Low-score correction (Dixon-Coles tau function)
    # ------------------------------------------------------------------

    def _tau(self, x: int, y: int, lam_h: float, lam_a: float) -> float:
        """Dixon-Coles low-score dependency correction factor.

        Parameters
        ----------
        x: home goals
        y: away goals
        lam_h: expected home goals
        lam_a: expected away goals
        """
        rho = self.rho
        if x == 0 and y == 0:
            return 1.0 - lam_h * lam_a * rho
        elif x == 1 and y == 0:
            return 1.0 + lam_a * rho
        elif x == 0 and y == 1:
            return 1.0 + lam_h * rho
        elif x == 1 and y == 1:
            return 1.0 - rho
        else:
            return 1.0

    # ------------------------------------------------------------------
    # Expected goals
    # ------------------------------------------------------------------

    def _lambda(
        self, home_team: str, away_team: str
    ) -> tuple[float, float]:
        """Return (lam_h, lam_a) for a given fixture.

        Raises
        ------
        ValueError
            If either team is not in the fitted parameter dictionaries.
        """
        for team in (home_team, away_team):
            if team not in self.attack:
                raise ValueError(
                    f"Unknown team '{team}': not in fitted model. "
                    "Call fit() first or check team name spelling."
                )
        lam_h = math.exp(
            self.attack[home_team] - self.defense[away_team] + self.home_adv
        )
        lam_a = math.exp(
            self.attack[away_team] - self.defense[home_team]
        )
        return lam_h, lam_a

    # ------------------------------------------------------------------
    # Fitting
    # ------------------------------------------------------------------

    def fit(
        self,
        matches_df: pd.DataFrame,
        time_decay_xi: float = 0.0018,
    ) -> None:
        """Fit the model parameters on historical match data.

        Parameters
        ----------
        matches_df:
            DataFrame with columns:
            ``date`` (datetime), ``home_team`` (str), ``away_team`` (str),
            ``home_goals`` (int), ``away_goals`` (int).
        time_decay_xi:
            Exponential time-decay rate per day.  Higher values discount
            older matches more heavily.  Default 0.0018 ≈ half-life ~1 year.
        """
        df = matches_df.copy()
        df["date"] = pd.to_datetime(df["date"])
        today = pd.Timestamp.now().normalize()

        # Time weights
        df["_w"] = np.exp(-time_decay_xi * (today - df["date"]).dt.days)

        # All teams
        teams = sorted(
            set(df["home_team"].tolist()) | set(df["away_team"].tolist())
        )
        n_teams = len(teams)
        team_idx = {t: i for i, t in enumerate(teams)}

        # ── Parameter vector layout ──────────────────────────────────────────
        # [attack_0 … attack_{n-1}, defense_0 … defense_{n-1}, home_adv]
        n_params = 2 * n_teams + 1

        # Initial values
        x0 = np.zeros(n_params)
        x0[:n_teams] = 1.0          # attack initialised to 1
        x0[n_teams : 2 * n_teams] = 0.0  # defense initialised to 0
        x0[-1] = 0.25               # home advantage

        rows = df.to_dict("records")

        def _neg_log_likelihood(params: np.ndarray) -> float:
            atk = params[:n_teams]
            dfs = params[n_teams : 2 * n_teams]
            hadv = params[-1]
            nll = 0.0
            for row in rows:
                hi = team_idx[row["home_team"]]
                ai = team_idx[row["away_team"]]
                lam_h = math.exp(atk[hi] - dfs[ai] + hadv)
                lam_a = math.exp(atk[ai] - dfs[hi])
                x = int(row["home_goals"])
                y = int(row["away_goals"])
                tau = self._tau(x, y, lam_h, lam_a)
                if tau <= 0:
                    tau = 1e-10
                log_p = (
                    poisson.logpmf(x, lam_h)
                    + poisson.logpmf(y, lam_a)
                    + math.log(tau)
                )
                nll -= row["_w"] * log_p
            return nll

        result = minimize(
            _neg_log_likelihood,
            x0,
            method="L-BFGS-B",
            options={"maxiter": 500, "ftol": 1e-9},
        )

        # Extract and normalise parameters (mean attack = 1)
        atk = result.x[:n_teams]
        dfs = result.x[n_teams : 2 * n_teams]
        hadv = float(result.x[-1])

        atk_mean = float(np.mean(atk))
        atk = atk - atk_mean  # log-space normalisation

        for i, team in enumerate(teams):
            self.attack[team] = float(atk[i])
            self.defense[team] = float(dfs[i])
        self.home_adv = hadv
        self.fitted = True

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict_probabilities(
        self, home_team: str, away_team: str
    ) -> dict[str, Any]:
        """Compute match outcome probabilities using the fitted model.

        Parameters
        ----------
        home_team, away_team:
            Team names (must have been seen during fit).

        Returns
        -------
        dict with keys:
            ``score_matrix``, ``home_win``, ``draw``, ``away_win``,
            ``btts``, ``over_15``, ``over_25``, ``over_35``,
            ``under_15``, ``under_25``, ``under_35``, ``btts_over25``,
            ``expected_home_goals``, ``expected_away_goals``.

        Raises
        ------
        ValueError
            If either team is unknown.
        """
        if not self.fitted:
            raise RuntimeError("Model has not been fitted yet. Call fit() first.")

        lam_h, lam_a = self._lambda(home_team, away_team)
        mg = self.max_goals

        # Build score matrix
        score_matrix = np.zeros((mg + 1, mg + 1))
        for x in range(mg + 1):
            for y in range(mg + 1):
                tau = self._tau(x, y, lam_h, lam_a)
                p = (
                    poisson.pmf(x, lam_h)
                    * poisson.pmf(y, lam_a)
                    * tau
                )
                score_matrix[x, y] = max(p, 0.0)

        # Normalise so probabilities sum exactly to 1
        total = score_matrix.sum()
        if total > 0:
            score_matrix /= total

        # Marginal outcomes
        home_win = float(np.sum(np.tril(score_matrix, -1)))   # x > y
        draw     = float(np.sum(np.diag(score_matrix)))
        away_win = float(np.sum(np.triu(score_matrix, 1)))    # y > x

        # Goals markets
        btts = 0.0
        over_15 = over_25 = over_35 = 0.0
        under_15 = under_25 = under_35 = 0.0
        btts_over25 = 0.0

        for x in range(mg + 1):
            for y in range(mg + 1):
                p = score_matrix[x, y]
                total_goals = x + y
                if x >= 1 and y >= 1:
                    btts += p
                    if total_goals >= 3:
                        btts_over25 += p
                if total_goals >= 2:
                    over_15 += p
                if total_goals >= 3:
                    over_25 += p
                if total_goals >= 4:
                    over_35 += p
                if total_goals <= 1:
                    under_15 += p
                if total_goals <= 2:
                    under_25 += p
                if total_goals <= 3:
                    under_35 += p

        return {
            "score_matrix":          score_matrix,
            "home_win":              home_win,
            "draw":                  draw,
            "away_win":              away_win,
            "btts":                  btts,
            "over_15":               over_15,
            "over_25":               over_25,
            "over_35":               over_35,
            "under_15":              under_15,
            "under_25":              under_25,
            "under_35":              under_35,
            "btts_over25":           btts_over25,
            "expected_home_goals":   lam_h,
            "expected_away_goals":   lam_a,
        }

    # ------------------------------------------------------------------
    # Team ratings
    # ------------------------------------------------------------------

    def get_team_ratings(self) -> pd.DataFrame:
        """Return a DataFrame of team attack/defense ratings.

        Returns
        -------
        pd.DataFrame with columns:
            ``team``, ``attack``, ``defense``, ``net_rating``
            (= attack - defense), sorted by ``net_rating`` descending.
        """
        rows = []
        for team in self.attack:
            atk = self.attack[team]
            dfs = self.defense[team]
            rows.append(
                {
                    "team":       team,
                    "attack":     atk,
                    "defense":    dfs,
                    "net_rating": atk - dfs,
                }
            )
        return (
            pd.DataFrame(rows)
            .sort_values("net_rating", ascending=False)
            .reset_index(drop=True)
        )
