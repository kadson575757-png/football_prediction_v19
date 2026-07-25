"""Chronological OOF generation for hierarchical base predictions."""

from __future__ import annotations

import numpy as np
import pandas as pd

from football_prediction_v19.analysis.v2180_hierarchical_winner import fit_hierarchical_model, predict_hierarchical


def chronological_oof_predictions(
    rows: pd.DataFrame,
    *,
    feature_groups: str,
    c: float,
    folds: int = 4,
) -> tuple[np.ndarray, pd.DataFrame]:
    dates = pd.to_datetime(rows["match_date"])
    unique_dates = np.array(sorted(dates.unique()))
    boundaries = np.linspace(0, len(unique_dates), folds + 2, dtype=int)
    predictions = np.full((len(rows), 3), np.nan)
    audits = []
    for fold in range(1, folds + 1):
        train_dates = unique_dates[:boundaries[fold]]
        validation_dates = unique_dates[boundaries[fold]:boundaries[fold + 1]]
        train_idx = np.flatnonzero(dates.isin(train_dates).to_numpy())
        validation_idx = np.flatnonzero(dates.isin(validation_dates).to_numpy())
        if len(train_idx) < 30 or not len(validation_idx):
            continue
        model = fit_hierarchical_model(rows.iloc[train_idx], feature_groups, c)
        predictions[validation_idx] = predict_hierarchical(model, rows.iloc[validation_idx])
        train_max = pd.to_datetime(rows.iloc[train_idx]["match_date"]).max()
        validation_min = pd.to_datetime(rows.iloc[validation_idx]["match_date"]).min()
        audits.append({
            "fold": fold,
            "train_count": len(train_idx),
            "validation_count": len(validation_idx),
            "train_max_date": train_max.date().isoformat(),
            "validation_min_date": validation_min.date().isoformat(),
            "chronological_clean": bool(train_max < validation_min),
            "in_sample_prediction_count": 0,
        })
    return predictions, pd.DataFrame(audits)


def complete_oof_with_prior(rows: pd.DataFrame, oof: np.ndarray) -> np.ndarray:
    """Fill the initial expanding-window segment with prematch primary probabilities.

    These are formula-based, non-fitted base outputs, not in-sample hierarchical predictions.
    """
    missing = np.isnan(oof).any(axis=1)
    oof[missing] = rows.loc[missing, [
        "base_home_probability", "base_draw_probability", "base_away_probability"
    ]].to_numpy()
    return oof
