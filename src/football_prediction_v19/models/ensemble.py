# -*- coding: utf-8 -*-
"""Ensemble predictor for Phase-10.

Combines LogisticRegression, GradientBoostingClassifier, and
RandomForestClassifier with equal weights.  Runs *parallel* to the
existing main model — it never replaces it.

No betting, ROI, or staking logic is present.
"""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression


class EnsemblePredictor:
    """Three-model soft-voting ensemble with agreement scoring.

    Parameters
    ----------
    models:
        List of three fitted-or-unfitted sklearn-compatible classifiers.
        If *None* (default), uses LR + GB + RF with fixed random seeds.
    """

    def __init__(self, models: list | None = None) -> None:
        if models is None:
            self.models: list = [
                LogisticRegression(max_iter=1000),
                GradientBoostingClassifier(n_estimators=50, random_state=42),
                RandomForestClassifier(n_estimators=50, random_state=42),
            ]
        else:
            self.models = list(models)

        self.model_names: list[str] = ["lr", "gb", "rf"]
        self.fitted: bool = False

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def fit(self, X, y) -> None:
        """Fit all three base models on *X*, *y*."""
        for m in self.models:
            m.fit(X, y)
        self.fitted = True

    # ------------------------------------------------------------------
    # Prediction helpers
    # ------------------------------------------------------------------

    def predict_proba_all(self, X) -> dict:
        """Return per-model probability arrays plus ensemble average and agreement.

        Returns
        -------
        dict with keys:
          "lr"         → np.ndarray shape (n, n_classes)
          "gb"         → np.ndarray shape (n, n_classes)
          "rf"         → np.ndarray shape (n, n_classes)
          "ensemble"   → np.ndarray shape (n, n_classes)  — mean of the three
          "agreement"  → float  — 0.0 / 0.5 / 1.0 per row, averaged over rows

        Raises
        ------
        RuntimeError if the predictor has not been fitted.
        """
        if not self.fitted:
            raise RuntimeError(
                "EnsemblePredictor has not been fitted yet. Call fit() first."
            )

        probas: dict = {}
        for name, model in zip(self.model_names, self.models):
            probas[name] = model.predict_proba(X)

        # Ensemble = simple average of the three probability matrices
        probas["ensemble"] = np.mean(
            [probas[n] for n in self.model_names], axis=0
        )

        # Agreement: per-row, check whether all three argmax classes match
        model_argmax = np.stack(
            [np.argmax(probas[n], axis=1) for n in self.model_names],
            axis=1,
        )  # shape: (n_rows, 3)

        row_agreements: list[float] = []
        for row in model_argmax:
            p0, p1, p2 = int(row[0]), int(row[1]), int(row[2])
            if p0 == p1 == p2:
                row_agreements.append(1.0)
            elif p0 == p1 or p1 == p2 or p0 == p2:
                row_agreements.append(0.5)
            else:
                row_agreements.append(0.0)

        # For a single row return that row's value; otherwise average
        if len(row_agreements) == 1:
            probas["agreement"] = row_agreements[0]
        else:
            probas["agreement"] = float(np.mean(row_agreements))

        return probas

    def predict_ensemble(self, X) -> np.ndarray:
        """Return the argmax class indices from the ensemble average probabilities."""
        result = self.predict_proba_all(X)
        return np.argmax(result["ensemble"], axis=1)

    def agreement_score(self, X) -> float:
        """Return the agreement score (0.0 / 0.5 / 1.0) for *X*.

        For a single-row input this is exactly one of {0.0, 0.5, 1.0}.
        For multi-row input this is the mean over rows.
        """
        return self.predict_proba_all(X)["agreement"]
