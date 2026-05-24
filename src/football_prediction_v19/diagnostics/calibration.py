# -*- coding: utf-8 -*-
"""Calibration reliability diagram (CSV-only, no matplotlib).

Computes the Expected Calibration Error (ECE) and produces a
reliability-diagram DataFrame that can be saved as CSV.

This module is a DIAGNOSTIC / RESEARCH tool only.
- No betting rules, no ROI, no staking.
- Does not change model probabilities.
- Kein matplotlib, kein PNG — only CSV output.

Public API
----------
reliability_diagram(probs, outcomes, n_bins, label) -> pd.DataFrame
save_calibration_csv(df, output_path) -> Path
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Union

import pandas as pd

__all__ = ["reliability_diagram", "save_calibration_csv"]

# Default output directory (relative to project root)
_DEFAULT_OUT_DIR = Path("outputs") / "diagnostics" / "calibration"


def reliability_diagram(
    probs: list[float],
    outcomes: list[int],
    n_bins: int = 10,
    label: str = "model",
) -> pd.DataFrame:
    """Compute calibration reliability data (no plot — CSV-ready DataFrame).

    Parameters
    ----------
    probs:
        Predicted probabilities in [0, 1].  One value per observation.
    outcomes:
        Actual binary outcomes (0 or 1).  Must be the same length as *probs*.
    n_bins:
        Number of equal-width probability bins spanning [0, 1].
        Bins with zero observations are excluded from the output.
    label:
        String label stored in every output row for identification.

    Returns
    -------
    pd.DataFrame
        One row per non-empty bin.  Columns:

        - ``bin_low``       : lower edge of the probability bin (inclusive)
        - ``bin_high``      : upper edge of the probability bin (exclusive for
                              all bins except the last, which is inclusive)
        - ``bin_center``    : midpoint = (bin_low + bin_high) / 2
        - ``mean_pred_prob``: mean of predicted probabilities in this bin
        - ``actual_rate``   : fraction of outcomes == 1 in this bin
        - ``n``             : number of observations in this bin
        - ``label``         : the *label* argument passed by the caller
        - ``ece``           : the overall ECE (same value on every row)

    Notes
    -----
    ECE formula::

        ECE = Σ  (|mean_pred_prob_b − actual_rate_b| × n_b / N)

    where the sum is over non-empty bins and N is the total number of
    observations.
    """
    if len(probs) != len(outcomes):
        raise ValueError(
            f"probs and outcomes must have equal length; "
            f"got len(probs)={len(probs)}, len(outcomes)={len(outcomes)}"
        )
    if n_bins < 1:
        raise ValueError(f"n_bins must be >= 1, got {n_bins}")

    if not probs:
        return _empty_output(label)

    total_n = len(probs)
    bin_width = 1.0 / n_bins

    rows: list[dict] = []
    for i in range(n_bins):
        lo = i * bin_width
        hi = (i + 1) * bin_width

        # Build bin mask: inclusive lo, exclusive hi — except the last bin which
        # is fully closed to capture prob == 1.0
        in_bin = [
            lo <= p < hi if i < n_bins - 1 else lo <= p <= hi
            for p in probs
        ]
        bin_probs    = [p for p, m in zip(probs, in_bin) if m]
        bin_outcomes = [o for o, m in zip(outcomes, in_bin) if m]

        n_bin = len(bin_probs)
        if n_bin == 0:
            continue  # exclude empty bins per spec

        mean_pred = sum(bin_probs) / n_bin
        actual_rt = sum(bin_outcomes) / n_bin
        rows.append({
            "bin_low":       round(lo, 10),
            "bin_high":      round(hi, 10),
            "bin_center":    round((lo + hi) / 2.0, 10),
            "mean_pred_prob": round(mean_pred, 6),
            "actual_rate":   round(actual_rt, 6),
            "n":             n_bin,
            "label":         label,
        })

    if not rows:
        return _empty_output(label)

    # Compute ECE
    ece = sum(
        abs(r["mean_pred_prob"] - r["actual_rate"]) * r["n"] / total_n
        for r in rows
    )
    ece = round(ece, 6)

    df = pd.DataFrame(rows)
    df["ece"] = ece
    return df


def save_calibration_csv(
    df: pd.DataFrame,
    output_path: Optional[Union[str, Path]] = None,
) -> Path:
    """Save a reliability-diagram DataFrame as CSV.

    Parameters
    ----------
    df:
        DataFrame returned by :func:`reliability_diagram`.
    output_path:
        Full path for the CSV file.  If *None*, defaults to
        ``outputs/diagnostics/calibration/calibration_<label>.csv``
        in the project root.

    Returns
    -------
    Path
        The path where the CSV was written.
    """
    if output_path is None:
        root = Path(__file__).resolve().parents[4]
        label = df["label"].iloc[0] if "label" in df.columns and not df.empty else "model"
        safe_label = str(label).replace(" ", "_").replace("/", "_")
        output_path = root / _DEFAULT_OUT_DIR / f"calibration_{safe_label}.csv"

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    return out


def _empty_output(label: str = "model") -> pd.DataFrame:
    """Return an empty DataFrame with the correct schema."""
    return pd.DataFrame(columns=[
        "bin_low", "bin_high", "bin_center",
        "mean_pred_prob", "actual_rate", "n", "label", "ece",
    ])


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _main() -> None:  # pragma: no cover
    """Demo: compute calibration from outputs/diagnostics/daily_recommendation_eval.csv."""
    root = Path(__file__).resolve().parents[4]
    eval_path = root / "outputs" / "diagnostics" / "daily_recommendation_eval.csv"

    if not eval_path.exists():
        print(f"[calibration] Eval file not found: {eval_path}", file=sys.stderr)
        sys.exit(1)

    df_eval = pd.read_csv(eval_path, low_memory=False)

    prob_col   = "model_home_prob"
    result_col = "type_success"

    if prob_col not in df_eval.columns or result_col not in df_eval.columns:
        print(f"[calibration] Required columns '{prob_col}' and '{result_col}' not found.",
              file=sys.stderr)
        sys.exit(1)

    sub = df_eval[[prob_col, result_col]].dropna()
    probs    = sub[prob_col].tolist()
    outcomes = [1 if str(x).lower() in ("true", "1", "yes") else 0
                for x in sub[result_col]]

    cal_df = reliability_diagram(probs, outcomes, n_bins=10, label="all_leagues")
    if not cal_df.empty:
        ece = cal_df["ece"].iloc[0]
        print(f"ECE (Expected Calibration Error): {ece:.4f}")
        print(cal_df.to_string(index=False))

    out = save_calibration_csv(cal_df)
    print(f"\nCalibration CSV written to {out}")


if __name__ == "__main__":
    _main()
