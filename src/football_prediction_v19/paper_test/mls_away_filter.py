"""MLS Away paper-test filter.

Validated signal (2024 and 2025 OOS backtests):
  - Away edge >= 0.04: +8.85% ROI (2024, 26 bets), +9.18% ROI (2025, 116 bets)
  - Away edge >= 0.05: +34.76% ROI (2024, 21 bets), +14.88% ROI (2025, 104 bets)

This module applies a strict filter on predict-fixtures output or backtest rows
and returns only the MLS Away candidates that cleared all gates.

PAPER TEST ONLY — not for live betting.
See docs/MLS_PAPER_TEST.md for rules and drawdown limits.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

MIN_EDGE: float = 0.04
MIN_CONTROL: float = 7.0
MAX_CHAOS: float = 7.0
STAKE: float = 1.0

OUTPUT_COLUMNS = [
    "date",
    "league",
    "home_team",
    "away_team",
    "pick",
    "odds_away",
    "model_away_prob",
    "edge",
    "control_score",
    "chaos_score",
    "status",
    "stake",
    "result",
    "profit",
]


def _get(row: pd.Series | dict[str, Any], key: str, default: Any = np.nan) -> Any:
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        v = row.get(key, default)
        return default if (isinstance(v, float) and np.isnan(v)) else v
    except (TypeError, AttributeError):
        return default


def _float(val: Any) -> float:
    try:
        f = float(val)
        return f if not np.isnan(f) else np.nan
    except (TypeError, ValueError):
        return np.nan


def _is_mls_away_candidate(
    row: pd.Series | dict[str, Any],
    min_edge: float = MIN_EDGE,
    min_control: float = MIN_CONTROL,
    max_chaos: float = MAX_CHAOS,
) -> bool:
    """Return True if this row passes all MLS Away paper-test gates."""
    # Must be MLS
    league = str(_get(row, "league", "")).strip()
    if league != "MLS":
        return False

    # Value pick must be Away (from predict-fixtures output)
    # Also accept backtest rows where value_pick == "Away"
    value_pick = str(_get(row, "value_pick", "")).strip()
    if value_pick != "Away":
        return False

    # Away odds must be present and > 1
    odds_away = _float(_get(row, "odds_away"))
    if np.isnan(odds_away) or odds_away <= 1.0:
        return False

    # Away edge must meet threshold
    edge_away = _float(_get(row, "edge_away"))
    if np.isnan(edge_away) or edge_away < min_edge:
        return False

    # Control score gate — skipped if column absent (backtest-bets already applied it)
    control = _float(_get(row, "control_score"))
    if not np.isnan(control) and control < min_control:
        return False

    # Chaos gate — skipped if column absent (backtest-bets already applied it)
    chaos = _float(_get(row, "chaos_score"))
    if not np.isnan(chaos) and chaos > max_chaos:
        return False

    return True


def filter_candidates(
    df: pd.DataFrame,
    min_edge: float = MIN_EDGE,
    min_control: float = MIN_CONTROL,
    max_chaos: float = MAX_CHAOS,
    status: str = "PENDING",
) -> pd.DataFrame:
    """Filter a predictions DataFrame to MLS Away paper-test candidates.

    Accepts output from `fpv19 predict-fixtures` (upcoming) or
    `fpv19 backtest-bets` (historical). Returns a normalised DataFrame
    with a fixed OUTPUT_COLUMNS schema.

    Parameters
    ----------
    df:
        Source DataFrame (predictions or backtest rows).
    min_edge:
        Minimum away edge required (default 0.04).
    min_control:
        Minimum control model score required (default 7.0).
    max_chaos:
        Maximum chaos score allowed (default 7.0).
    status:
        Value for the status column on all output rows ("PENDING" for
        upcoming fixtures, "SETTLED" for historical rows).
    """
    mask = df.apply(
        lambda r: _is_mls_away_candidate(r, min_edge, min_control, max_chaos),
        axis=1,
    )
    src = df.loc[mask].copy()

    rows: list[dict[str, Any]] = []
    for _, r in src.iterrows():
        # Determine result and profit from historical data if available
        result = _get(r, "result", "")
        profit = _float(_get(r, "profit"))
        if np.isnan(profit):
            # Calculate profit from result for historical rows where profit column absent
            result_str = str(result).strip() if result else ""
            odds_away = _float(_get(r, "odds_away"))
            if result_str == "A" and not np.isnan(odds_away):
                profit = round(float(odds_away) - 1.0, 4)
            elif result_str in ("H", "D"):
                profit = -1.0
            else:
                profit = np.nan

        rows.append({
            "date": str(_get(r, "date", "")),
            "league": str(_get(r, "league", "MLS")),
            "home_team": str(_get(r, "home_team", "")),
            "away_team": str(_get(r, "away_team", "")),
            "pick": "Away",
            "odds_away": round(_float(_get(r, "odds_away")), 2),
            "model_away_prob": round(_float(_get(r, "prob_away")), 4),
            "edge": round(_float(_get(r, "edge_away")), 4),
            "control_score": round(_float(_get(r, "control_score")), 2) if not np.isnan(_float(_get(r, "control_score"))) else np.nan,
            "chaos_score": round(_float(_get(r, "chaos_score")), 2) if not np.isnan(_float(_get(r, "chaos_score"))) else np.nan,
            "status": status,
            "stake": STAKE,
            "result": str(result).strip() if result else "",
            "profit": profit,
        })

    out = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    return out.reset_index(drop=True)


def append_candidates(
    candidates: pd.DataFrame,
    ledger_path: str | Path,
) -> pd.DataFrame:
    """Append new candidates to an existing ledger CSV, avoiding duplicates.

    Deduplication key: (date, home_team, away_team).
    Returns the updated ledger DataFrame.
    """
    ledger_path = Path(ledger_path)
    if ledger_path.exists():
        existing = pd.read_csv(ledger_path)
        key_cols = ["date", "home_team", "away_team"]
        existing_keys = set(
            zip(existing["date"].astype(str), existing["home_team"].astype(str), existing["away_team"].astype(str))
        )
        new_rows = candidates[
            ~candidates.apply(
                lambda r: (str(r["date"]), str(r["home_team"]), str(r["away_team"])) in existing_keys,
                axis=1,
            )
        ]
        updated = pd.concat([existing, new_rows], ignore_index=True).convert_dtypes()
    else:
        updated = candidates.copy()
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    updated.to_csv(ledger_path, index=False)
    return updated
