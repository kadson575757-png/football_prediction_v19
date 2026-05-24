# -*- coding: utf-8 -*-
"""Walk-forward evaluation harness for the Dixon-Coles Poisson model.

DIAGNOSTIC / ANALYTICAL LAYER ONLY.
- Runs parallel to the existing ML classifier.
- No betting, ROI, or staking logic.

Public API
----------
evaluate_poisson_walk_forward(matches_df, min_warmup, time_decay_xi) -> pd.DataFrame
"""
from __future__ import annotations

import pandas as pd

from .dixon_coles import DixonColesModel

__all__ = ["evaluate_poisson_walk_forward"]


def _assert_no_leakage(
    prior_df: pd.DataFrame,
    cutoff_date: pd.Timestamp,
    label: str = "",
) -> None:
    """Assert that *prior_df* contains NO rows with date >= *cutoff_date*.

    Mirrors the Phase-1 leakage guard from run_season_replay_audit.py.
    """
    if prior_df.empty:
        return
    max_date = prior_df["date"].max()
    ctx = f" [{label}]" if label else ""
    assert max_date < cutoff_date, (
        f"Leakage detected{ctx}: prior_df max date "
        f"{max_date} >= cutoff {cutoff_date}"
    )
    leaked_count = int((prior_df["date"] >= cutoff_date).sum())
    assert leaked_count == 0, (
        f"Leakage detected{ctx}: {leaked_count} row(s) in prior_df "
        f"have date >= cutoff {cutoff_date}"
    )


def evaluate_poisson_walk_forward(
    matches_df: pd.DataFrame,
    min_warmup: int = 100,
    time_decay_xi: float = 0.0018,
) -> pd.DataFrame:
    """Walk-forward evaluation of the Dixon-Coles model on historical matches.

    For each match (chronologically), trains the model on all prior matches
    and evaluates predictions against the actual outcome.

    Parameters
    ----------
    matches_df:
        DataFrame with columns:
        ``date`` (datetime-like), ``home_team``, ``away_team``,
        ``home_goals`` (int), ``away_goals`` (int).
    min_warmup:
        Minimum number of prior matches required before evaluation starts.
        Matches with fewer prior rows are skipped.
    time_decay_xi:
        Exponential time-decay rate forwarded to DixonColesModel.fit().

    Returns
    -------
    pd.DataFrame with columns:
        ``date``, ``home_team``, ``away_team``,
        ``actual_home_goals``, ``actual_away_goals``,
        ``dc_home_win_prob``, ``dc_draw_prob``, ``dc_away_win_prob``,
        ``dc_btts_prob``, ``dc_over25_prob``, ``dc_under35_prob``,
        ``dc_home_correct``, ``dc_btts_correct``, ``dc_under35_correct``.
    """
    df = matches_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    records = []

    for i in range(len(df)):
        match = df.iloc[i]
        cutoff = match["date"]
        prior_df = df[df["date"] < cutoff].copy()

        if len(prior_df) < min_warmup:
            continue

        # Leakage guard (Phase-1 integrity check)
        _assert_no_leakage(prior_df, cutoff, label=f"row {i}")

        model = DixonColesModel()
        model.fit(prior_df, time_decay_xi=time_decay_xi)

        home = str(match["home_team"])
        away = str(match["away_team"])

        # Skip if either team not in training data
        try:
            probs = model.predict_probabilities(home, away)
        except ValueError:
            continue

        actual_hg = int(match["home_goals"])
        actual_ag = int(match["away_goals"])
        actual_home_win = actual_hg > actual_ag
        actual_btts     = actual_hg >= 1 and actual_ag >= 1
        actual_under35  = (actual_hg + actual_ag) <= 3

        dc_home_correct  = bool(probs["home_win"] > 0.5 and actual_home_win)
        dc_btts_correct  = bool(probs["btts"]     > 0.5 and actual_btts)
        dc_under35_correct = bool(probs["under_35"] > 0.6 and actual_under35)

        records.append(
            {
                "date":               match["date"],
                "home_team":          home,
                "away_team":          away,
                "actual_home_goals":  actual_hg,
                "actual_away_goals":  actual_ag,
                "dc_home_win_prob":   probs["home_win"],
                "dc_draw_prob":       probs["draw"],
                "dc_away_win_prob":   probs["away_win"],
                "dc_btts_prob":       probs["btts"],
                "dc_over25_prob":     probs["over_25"],
                "dc_under35_prob":    probs["under_35"],
                "dc_home_correct":    dc_home_correct,
                "dc_btts_correct":    dc_btts_correct,
                "dc_under35_correct": dc_under35_correct,
            }
        )

    if not records:
        return pd.DataFrame(
            columns=[
                "date", "home_team", "away_team",
                "actual_home_goals", "actual_away_goals",
                "dc_home_win_prob", "dc_draw_prob", "dc_away_win_prob",
                "dc_btts_prob", "dc_over25_prob", "dc_under35_prob",
                "dc_home_correct", "dc_btts_correct", "dc_under35_correct",
            ]
        )

    return pd.DataFrame(records)
