# -*- coding: utf-8 -*-
"""Miss-cluster analysis for daily recommendation evaluation.

Identifies systematic failure patterns by grouping miss rows across
contextual dimensions (league, subtype, tier, season phase).

This module is a DIAGNOSTIC / RESEARCH tool only.
- No betting rules, no ROI, no staking.
- Does not change model probabilities or tier logic.
- Adds new analytical output only.

Public API
----------
cluster_misses(eval_df) -> pd.DataFrame
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import pandas as pd

__all__ = ["cluster_misses"]

# Minimum group size to be included in the output
_MIN_N: int = 5

# Miss-rate threshold to appear in output at all
_MISS_RATE_THRESHOLD: float = 0.50

# Miss-rate at or above which a cluster is labelled CRITICAL
_CRITICAL_THRESHOLD: float = 0.70

# Dimension columns used for grouping
_GROUP_COLS: list[str] = [
    "league",
    "recommended_market_subtype",
    "market_tier",
    "season_phase",
]

# Required input columns (others are optional and silently ignored)
_REQUIRED_COLS: frozenset[str] = frozenset({"type_success"})


def cluster_misses(eval_df: pd.DataFrame) -> pd.DataFrame:
    """Identify systematic miss patterns across contextual dimensions.

    Parameters
    ----------
    eval_df:
        Evaluation DataFrame.  Must contain at least ``type_success``
        (bool or coercible).  Optional columns that improve results:
        ``league``, ``recommended_market_subtype``, ``market_tier``,
        ``season_phase``.  Missing optional columns are filled with
        ``"unknown"`` so the function never raises on partial input.

    Returns
    -------
    pd.DataFrame
        One row per miss cluster that passes the n>=5 AND miss_rate>=0.50
        filter, sorted by ``miss_rate`` DESC.  Columns:

        - ``group_key``     : pipe-separated label e.g. "EPL | UNDER_35 | A_TIER | mid"
        - ``n``             : total rows in that dimension combination
        - ``miss_count``    : rows where type_success == False
        - ``miss_rate``     : miss_count / n  (float 0-1)
        - ``warning_level`` : ``"CRITICAL"`` if miss_rate >= 0.70, else ``"WARNING"``
    """
    if eval_df is None or eval_df.empty:
        return _empty_output()

    df = eval_df.copy()

    # Coerce type_success to nullable bool
    df["_ts"] = df["type_success"].apply(_coerce_bool)

    # Fill missing group columns with "unknown"
    for col in _GROUP_COLS:
        if col not in df.columns:
            df[col] = "unknown"
        else:
            df[col] = df[col].fillna("unknown").astype(str).str.strip()
            df[col] = df[col].replace({"": "unknown", "nan": "unknown", "None": "unknown"})

    # Misses = rows where type_success is definitively False (not NaN)
    miss_mask = df["_ts"] == False  # noqa: E712  (NaN-safe: NaN != False)
    df["_is_miss"] = miss_mask

    rows: list[dict] = []
    for keys, grp in df.groupby(_GROUP_COLS, sort=False):
        n = len(grp)
        # Only consider rows where type_success is not NaN for the denominator
        evaluated = grp["_ts"].notna()
        n_eval = int(evaluated.sum())
        if n_eval < _MIN_N:
            continue
        miss_count = int(grp["_is_miss"].sum())
        miss_rate = miss_count / n_eval

        if miss_rate < _MISS_RATE_THRESHOLD:
            continue

        group_key = " | ".join(str(k) for k in (keys if isinstance(keys, tuple) else (keys,)))
        warning_level = "CRITICAL" if miss_rate >= _CRITICAL_THRESHOLD else "WARNING"

        rows.append({
            "group_key":     group_key,
            "n":             n_eval,
            "miss_count":    miss_count,
            "miss_rate":     round(miss_rate, 4),
            "warning_level": warning_level,
        })

    if not rows:
        return _empty_output()

    out = pd.DataFrame(rows)
    out = out.sort_values("miss_rate", ascending=False).reset_index(drop=True)
    return out


def _empty_output() -> pd.DataFrame:
    """Return an empty DataFrame with the correct schema."""
    return pd.DataFrame(columns=["group_key", "n", "miss_count", "miss_rate", "warning_level"])


def _coerce_bool(val) -> Optional[bool]:
    """Coerce to True/False/None (NaN-safe)."""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, float):
        if val != val:  # NaN check
            return None
        return bool(val)
    if isinstance(val, int):
        return bool(val)
    s = str(val).strip().lower()
    if s in ("true", "1", "yes"):
        return True
    if s in ("false", "0", "no"):
        return False
    return None


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _main() -> None:  # pragma: no cover
    """Run miss-cluster analysis on outputs/diagnostics/daily_recommendation_eval.csv."""
    root = Path(__file__).resolve().parents[4]
    eval_path = root / "outputs" / "diagnostics" / "daily_recommendation_eval.csv"
    out_path  = root / "outputs" / "diagnostics" / "miss_clusters.csv"

    if not eval_path.exists():
        print(f"[miss_clusters] Eval file not found: {eval_path}", file=sys.stderr)
        print("  Run evaluate_daily_recommendations.py first.", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(eval_path, low_memory=False)
    result = cluster_misses(df)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out_path, index=False)

    print(f"Miss clusters written to {out_path}  ({len(result)} clusters)")
    critical = result[result["warning_level"] == "CRITICAL"]
    warnings = result[result["warning_level"] == "WARNING"]
    print(f"  CRITICAL: {len(critical)}   WARNING: {len(warnings)}")
    if not critical.empty:
        print("\nTop CRITICAL clusters:")
        for _, row in critical.head(5).iterrows():
            print(f"  {row['group_key']:<60}  miss={row['miss_rate']:.1%}  n={row['n']}")


if __name__ == "__main__":
    _main()
