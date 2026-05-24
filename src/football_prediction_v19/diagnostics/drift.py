# -*- coding: utf-8 -*-
"""Rolling performance drift monitor.

Detects systematic changes in recommendation accuracy over time by computing
hit-rate in rolling weekly windows and flagging windows that fall significantly
below the overall baseline.

This module is a DIAGNOSTIC / RESEARCH tool only.
- No betting rules, no ROI, no staking.
- Does not change model probabilities or tier logic.

Public API
----------
rolling_performance(eval_df, window_weeks, date_col) -> pd.DataFrame
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

__all__ = ["rolling_performance"]

# Hit-rate must be at least this many percentage points below the overall
# baseline for a DRIFT_WARNING to be flagged.
_DRIFT_THRESHOLD: float = 0.08

# Minimum evaluatable rows in a window for it to appear in the output
_MIN_WINDOW_N: int = 1


def rolling_performance(
    eval_df: pd.DataFrame,
    window_weeks: int = 8,
    date_col: str = "match_date",
) -> pd.DataFrame:
    """Compute rolling weekly hit-rate and detect performance drift.

    Parameters
    ----------
    eval_df:
        Evaluation DataFrame.  Must contain:

        - *date_col* (default ``"match_date"``): datetime-parseable date column.
        - ``type_success``: bool or bool-coercible success indicator.

    window_weeks:
        Width of the rolling window in calendar weeks.
    date_col:
        Name of the date column.  Parsed via ``pd.to_datetime`` so strings
        in ISO-8601 format (``"YYYY-MM-DD"``) work fine.

    Returns
    -------
    pd.DataFrame
        One row per rolling window (windows overlap by window_weeks-1 weeks).
        Columns:

        - ``window_start``  : first date in the window (pd.Timestamp)
        - ``window_end``    : last date in the window
        - ``n``             : number of evaluatable rows (type_success not NaN)
        - ``hit_rate``      : fraction where type_success == True
        - ``overall_rate``  : global hit_rate across the entire eval_df
        - ``drift_flag``    : ``"DRIFT_WARNING"`` or ``""``
    """
    if eval_df is None or eval_df.empty:
        return _empty_output()

    df = eval_df.copy()

    # Resolve date column — try match_date first, then date
    if date_col not in df.columns:
        alt = "date"
        if alt in df.columns:
            date_col = alt
        else:
            return _empty_output()

    df["_date"] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=["_date"])
    if df.empty:
        return _empty_output()

    # Coerce type_success
    df["_ts"] = df["type_success"].apply(_coerce_bool)
    evaluated = df[df["_ts"].notna()].copy()

    if evaluated.empty:
        return _empty_output()

    evaluated = evaluated.sort_values("_date").reset_index(drop=True)

    # Overall baseline
    overall_n = len(evaluated)
    overall_hits = int((evaluated["_ts"] == True).sum())  # noqa: E712
    overall_rate = overall_hits / overall_n if overall_n > 0 else 0.0

    window_delta = pd.Timedelta(weeks=window_weeks)
    all_dates = evaluated["_date"].sort_values().reset_index(drop=True)

    rows: list[dict] = []
    # Slide a window starting at each unique date
    seen_starts: set = set()
    for start_date in all_dates:
        # Normalise to week-start (Monday) to avoid duplicate windows
        week_start = start_date - pd.Timedelta(days=start_date.dayofweek)
        if week_start in seen_starts:
            continue
        seen_starts.add(week_start)

        end_date = week_start + window_delta - pd.Timedelta(days=1)
        mask = (evaluated["_date"] >= week_start) & (evaluated["_date"] <= end_date)
        window_rows = evaluated[mask]

        n = len(window_rows)
        if n < _MIN_WINDOW_N:
            continue

        hits = int((window_rows["_ts"] == True).sum())  # noqa: E712
        hit_rate = hits / n

        drift = (
            "DRIFT_WARNING"
            if hit_rate < (overall_rate - _DRIFT_THRESHOLD)
            else ""
        )

        rows.append({
            "window_start": week_start,
            "window_end":   end_date,
            "n":            n,
            "hit_rate":     round(hit_rate, 4),
            "overall_rate": round(overall_rate, 4),
            "drift_flag":   drift,
        })

    if not rows:
        return _empty_output()

    out = pd.DataFrame(rows).sort_values("window_start").reset_index(drop=True)
    return out


def _empty_output() -> pd.DataFrame:
    return pd.DataFrame(columns=[
        "window_start", "window_end", "n",
        "hit_rate", "overall_rate", "drift_flag",
    ])


def _coerce_bool(val):
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, float):
        if val != val:
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
    root = Path(__file__).resolve().parents[4]
    eval_path = root / "outputs" / "diagnostics" / "daily_recommendation_eval.csv"
    out_path  = root / "outputs" / "diagnostics" / "drift_monitor.csv"

    if not eval_path.exists():
        print(f"[drift] Eval file not found: {eval_path}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(eval_path, low_memory=False)
    # The evaluator uses 'date' not 'match_date'
    result = rolling_performance(df, window_weeks=8, date_col="date")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out_path, index=False)
    print(f"Drift monitor written to {out_path}  ({len(result)} windows)")

    drift_rows = result[result["drift_flag"] == "DRIFT_WARNING"]
    if not drift_rows.empty:
        print(f"\n⚠️  {len(drift_rows)} DRIFT_WARNING window(s) detected:")
        for _, r in drift_rows.iterrows():
            print(f"  {r['window_start'].date()} – {r['window_end'].date()}"
                  f"  hit={r['hit_rate']:.1%}  overall={r['overall_rate']:.1%}")
    else:
        print("No drift warnings detected.")


if __name__ == "__main__":
    _main()
