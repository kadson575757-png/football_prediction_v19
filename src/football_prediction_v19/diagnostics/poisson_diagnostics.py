# -*- coding: utf-8 -*-
"""Dixon-Coles diagnostic overlay for existing market tier recommendations.

DIAGNOSTIC / ANALYTICAL LAYER ONLY.
- Adds supplementary DC-based fields to existing tier results.
- Does NOT modify existing tier scores, model probabilities, or tier logic.
- No betting, ROI, or staking logic.

Public API
----------
poisson_market_tier_override(dc_probs, existing_tier, existing_subtype) -> dict
"""
from __future__ import annotations

__all__ = ["poisson_market_tier_override"]

_A_B_TIERS = frozenset({"A_TIER", "B_TIER"})


def poisson_market_tier_override(
    dc_probs: dict,
    existing_tier: str,
    existing_subtype: str,
) -> dict:
    """Produce a DC-based diagnostic overlay for a market tier recommendation.

    This function does NOT modify the existing tier or score; it returns a
    supplementary dict with additional fields only.

    Parameters
    ----------
    dc_probs:
        Output of ``DixonColesModel.predict_probabilities()``.
    existing_tier:
        The ``market_tier`` value from ``build_market_tier()``.
    existing_subtype:
        The ``recommended_market_subtype`` value.

    Returns
    -------
    dict with keys:
        ``dc_btts_prob`` (float),
        ``dc_under35_prob`` (float),
        ``dc_over25_prob`` (float),
        ``dc_tier_note`` (str),
        ``dc_confirms_tier`` (bool),
        ``market_tier`` (str — may be downgraded to C_TIER if DC conflicts).
    """
    dc_btts    = float(dc_probs.get("btts",     0.0))
    dc_u35     = float(dc_probs.get("under_35", 0.0))
    dc_o25     = float(dc_probs.get("over_25",  0.0))

    subtype_up = existing_subtype.upper() if existing_subtype else ""
    dc_confirms = True
    note = ""

    if subtype_up == "UNDER_35" and dc_u35 < 0.45:
        dc_confirms = False
        note = f"DC conflicts: under35_prob={dc_u35:.2f}"

    elif subtype_up == "BTTS" and dc_btts < 0.40:
        dc_confirms = False
        note = f"DC conflicts: btts_prob={dc_btts:.2f}"

    # Apply tier downgrade if DC conflicts and tier is A or B
    output_tier = existing_tier
    if not dc_confirms and existing_tier in _A_B_TIERS:
        output_tier = "C_TIER"
        note += " [DC_DOWNGRADE]"

    return {
        "dc_btts_prob":    dc_btts,
        "dc_under35_prob": dc_u35,
        "dc_over25_prob":  dc_o25,
        "dc_tier_note":    note,
        "dc_confirms_tier": dc_confirms,
        "market_tier":     output_tier,
    }
