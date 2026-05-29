# -*- coding: utf-8 -*-
"""Ensemble-based market-tier override for Phase-10.

Applies consensus / disagreement / split signals from EnsemblePredictor
to the market-tier assigned by build_market_tier().

Rules (applied in this order):
  1. HARD_NO_GO is always preserved — ensemble can never upgrade it.
  2. agreement == 1.0 AND existing_tier == "A_TIER"
       → market_tier = "SUPER_A_TIER"
  3. agreement == 0.0 AND existing_tier in ("A_TIER", "B_TIER")
       → market_tier = "C_TIER"
  4. agreement == 0.5
       → tier unchanged; flag ENSEMBLE_SPLIT added
  5. Otherwise: no change

No betting, ROI, or staking logic is present.
"""
from __future__ import annotations

from collections import Counter
from typing import Any


ENSEMBLE_AGREEMENT_ORDER: tuple[str, ...] = ("HIGH", "MEDIUM", "LOW", "NONE")
_OLD_AGREEMENT_MAP: dict[str, str] = {
    "CONSENSUS": "HIGH",
    "SPLIT": "MEDIUM",
    "DISAGREEMENT": "LOW",
    "1": "HIGH",
    "1.0": "HIGH",
    "0.5": "MEDIUM",
    "0": "LOW",
    "0.0": "LOW",
}


def normalize_ensemble_agreement(value: Any) -> str:
    """Normalize old/new ensemble agreement values to HIGH/MEDIUM/LOW/NONE."""
    if value is None:
        return "NONE"
    text = str(value).strip().upper()
    if not text or text in {"NAN", "NONE", "NULL"}:
        return "NONE"
    if text in ENSEMBLE_AGREEMENT_ORDER:
        return text
    return _OLD_AGREEMENT_MAP.get(text, "NONE")


def compute_ensemble_agreement(predictions: dict[str, str]) -> tuple[str, str]:
    """Return standardized ensemble agreement label and readable diagnostic note."""
    clean_predictions = {
        str(name): str(pred).strip().upper()
        for name, pred in predictions.items()
        if str(pred).strip()
    }
    n_models = len(clean_predictions)
    if n_models < 2:
        return (
            "NONE",
            "Only one model prediction available; ensemble agreement not computed.",
        )

    counts = Counter(clean_predictions.values())
    direction, top_count = counts.most_common(1)[0]
    rendered = " | ".join(
        f"{name}={pred}" for name, pred in clean_predictions.items()
    )

    if top_count == n_models:
        return (
            "HIGH",
            f"All available models agree on {direction} ({top_count}/{n_models}): {rendered}",
        )
    if top_count > n_models / 2:
        return (
            "MEDIUM",
            f"Majority agreement on {direction} ({top_count}/{n_models}): {rendered}",
        )
    return (
        "LOW",
        f"No clear majority across available model predictions: {rendered}",
    )


def apply_ensemble_override(
    existing_tier: str,
    existing_score: int,
    agreement: float,
    ensemble_predictions: dict,
) -> dict[str, Any]:
    """Apply ensemble agreement signal to the existing market tier.

    Parameters
    ----------
    existing_tier:
        The ``market_tier`` value produced by ``build_market_tier()``.
    existing_score:
        The ``market_tier_score`` (0-100) for informational use.
    agreement:
        The agreement score from ``EnsemblePredictor.agreement_score()``:
        ``1.0`` (all three agree), ``0.5`` (two agree), or ``0.0`` (none agree).
    ensemble_predictions:
        Raw dict from ``EnsemblePredictor.predict_proba_all()`` (may be empty).

    Returns
    -------
    dict with keys:
      "market_tier"        — possibly overridden tier
      "market_tier_reason" — explanation string
      "market_tier_flags"  — list of flag strings
      "ensemble_agreement" — "HIGH" | "MEDIUM" | "LOW" | "NONE"
      "ensemble_note"      — readable agreement diagnostic
    """
    market_tier = str(existing_tier)
    reason: str = ""
    flags: list[str] = []

    # -- standardized ensemble output based on numeric legacy signal ---------
    ensemble_agreement = normalize_ensemble_agreement(agreement)
    if ensemble_agreement == "HIGH":
        ensemble_note = "All available models agree; ensemble agreement is HIGH."
    elif ensemble_agreement == "MEDIUM":
        ensemble_note = "A majority of available models agree; ensemble agreement is MEDIUM."
    elif ensemble_agreement == "LOW":
        ensemble_note = "No clear majority across available model predictions; ensemble agreement is LOW."
    else:
        ensemble_note = "Only one model prediction available; ensemble agreement not computed."

    # -- Rule 1: HARD_NO_GO is immune to any ensemble override ---------------
    if market_tier == "HARD_NO_GO":
        # No tier change; no tier flags; just record the ensemble metadata.
        return {
            "market_tier":        market_tier,
            "market_tier_reason": reason,
            "market_tier_flags":  flags,
            "ensemble_agreement": ensemble_agreement,
            "ensemble_note":      ensemble_note,
        }

    # -- Rule 2: Full consensus on an A_TIER match → SUPER_A_TIER -----------
    if agreement == 1.0 and market_tier == "A_TIER":
        market_tier = "SUPER_A_TIER"
        reason += " [ENSEMBLE_CONSENSUS]"
        flags += ["SUPER_A_TIER"]

    # -- Rule 3: Full disagreement downgrades A/B_TIER to C_TIER -------------
    elif agreement == 0.0 and market_tier in ("A_TIER", "B_TIER"):
        market_tier = "C_TIER"
        reason += " [ENSEMBLE_DISAGREEMENT]"
        flags += ["ENSEMBLE_DISAGREEMENT"]

    # -- Rule 4: Split — add informational flag, no tier change --------------
    elif agreement == 0.5:
        flags += ["ENSEMBLE_SPLIT"]

    # -- Rule 5: No change (e.g. agreement==1.0 but tier is C_TIER / other) --
    # (market_tier remains as-is, reason/flags stay empty)

    return {
        "market_tier":        market_tier,
        "market_tier_reason": reason.strip(),
        "market_tier_flags":  flags,
        "ensemble_agreement": ensemble_agreement,
        "ensemble_note":      ensemble_note,
    }
