"""League-aware diagnostic report profile layer.

This module adds contextual interpretation fields to a recommendation dict
based on empirical walk-forward evaluation results across 6 leagues.

It is a REPORT INTERPRETATION LAYER ONLY.
- No betting rules, no ROI optimisation, no paper-test rules.
- Does not change recommended_market_type or recommended_market_subtype.
- Does not alter probability generation.
- Adds new fields only; never removes existing ones.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["apply_league_market_profile", "LEAGUE_PROFILES"]


# ---------------------------------------------------------------------------
# League profile definitions
# Empirical basis: walk-forward aggregate (2,920 evaluatable matches, 6 leagues)
# ---------------------------------------------------------------------------

#: Each entry describes the evidence-based profile for one league.
#: Keys:
#:   profile_name     - short machine-readable label
#:   preferred_types  - market types with strong evidence (n>=50, >=70%)
#:   preferred_subtypes - subtypes promoted by this league's characteristics
#:   suppressed_subtypes - subtypes with weak evidence (n>=50, <55%)
#:   allowed_subtypes    - subtypes explicitly allowed even if cross-league weak
#:   notes               - human-readable description
#:   warnings_if         - list of (field, values, message) tuples that trigger
#:                         a league_warning_flags entry

LEAGUE_PROFILES: dict[str, dict[str, Any]] = {
    "MLS": {
        "profile_name": "mls_volatile",
        "preferred_types": ["AVOID", "DOUBLE_CHANCE", "UNDER"],
        "preferred_subtypes": ["DOUBLE_CHANCE_1X", "DOUBLE_CHANCE_X2", "UNDER_35"],
        "suppressed_subtypes": ["BOTH_OVER25_BTTS", "BTTS"],
        "allowed_subtypes": [],
        "notes": (
            "MLS low-sample/custom profile — World Cup break, travel and "
            "rotation effects; treat goal-combo markets cautiously."
        ),
        "warnings_if": [
            (
                "recommended_market_subtype",
                {"BOTH_OVER25_BTTS", "BTTS"},
                "MLS low-sample/custom profile — World Cup break, travel and rotation effects; treat goal-combo markets cautiously.",
            ),
        ],
    },
    "Major League Soccer": {
        "profile_name": "mls_volatile",
        "preferred_types": ["AVOID", "DOUBLE_CHANCE", "UNDER"],
        "preferred_subtypes": ["DOUBLE_CHANCE_1X", "DOUBLE_CHANCE_X2", "UNDER_35"],
        "suppressed_subtypes": ["BOTH_OVER25_BTTS", "BTTS"],
        "allowed_subtypes": [],
        "notes": (
            "MLS low-sample/custom profile — World Cup break, travel and "
            "rotation effects; treat goal-combo markets cautiously."
        ),
        "warnings_if": [
            (
                "recommended_market_subtype",
                {"BOTH_OVER25_BTTS", "BTTS"},
                "MLS low-sample/custom profile — World Cup break, travel and rotation effects; treat goal-combo markets cautiously.",
            ),
        ],
    },
    "La Liga": {
        "profile_name": "la_liga_control",
        "preferred_types": ["AVOID", "DOUBLE_CHANCE", "UNDER"],
        "preferred_subtypes": ["UNDER_35", "DOUBLE_CHANCE_1X", "DOUBLE_CHANCE_X2"],
        "suppressed_subtypes": ["OVER_25", "BTTS", "BOTH_OVER25_BTTS"],
        "allowed_subtypes": [],
        "notes": (
            "La Liga is a lower-scoring, controlled league. "
            "UNDER_35 shows 92.7% accuracy (n=41). "
            "OVER_25 and BTTS have poor evidence; BOTH_OVER25_BTTS is unreliable."
        ),
        "warnings_if": [
            (
                "recommended_market_subtype",
                {"OVER_25", "BTTS", "BOTH_OVER25_BTTS"},
                "La Liga: goals subtype has poor walk-forward evidence — treat with caution.",
            ),
        ],
    },
    "Serie A": {
        "profile_name": "serie_a_control",
        "preferred_types": ["AVOID", "DOUBLE_CHANCE", "UNDER"],
        "preferred_subtypes": ["UNDER_35", "DOUBLE_CHANCE_1X", "DOUBLE_CHANCE_X2"],
        "suppressed_subtypes": ["BOTH_OVER25_BTTS"],
        "allowed_subtypes": ["BTTS"],
        "notes": (
            "Serie A is a control-heavy, low-to-mid scoring league. "
            "UNDER_35 and DOUBLE_CHANCE are well-supported. "
            "BOTH_OVER25_BTTS is unreliable; BTTS_OVER acceptable only with clear signal."
        ),
        "warnings_if": [
            (
                "recommended_market_subtype",
                {"BOTH_OVER25_BTTS"},
                "Serie A: BOTH_OVER25_BTTS has weak cross-league evidence.",
            ),
        ],
    },
    "Eredivisie": {
        "profile_name": "eredivisie_goals",
        "preferred_types": ["AVOID", "DOUBLE_CHANCE", "BTTS_OVER", "UNDER"],
        "preferred_subtypes": ["OVER_25", "DOUBLE_CHANCE_1X", "DOUBLE_CHANCE_X2"],
        "suppressed_subtypes": ["BOTH_OVER25_BTTS"],
        "allowed_subtypes": ["OVER_25", "BTTS"],
        "notes": (
            "Eredivisie is a high-scoring, volatile goals league. "
            "OVER_25 is viable here (65.5%) unlike most other leagues. "
            "BOTH_OVER25_BTTS remains unreliable even in this goals context."
        ),
        "warnings_if": [
            (
                "recommended_market_subtype",
                {"BOTH_OVER25_BTTS"},
                "Eredivisie: BOTH_OVER25_BTTS unreliable even in goals league.",
            ),
        ],
    },
    "2. Bundesliga": {
        "profile_name": "bundesliga2_goals_volatile",
        "preferred_types": ["AVOID", "DOUBLE_CHANCE"],
        "preferred_subtypes": ["DOUBLE_CHANCE_1X", "DOUBLE_CHANCE_X2"],
        "suppressed_subtypes": ["UNDER_35", "BOTH_OVER25_BTTS"],
        "allowed_subtypes": ["BTTS", "OVER_25"],
        "notes": (
            "2.Bundesliga combines goals and volatility. "
            "AVOID is the strongest subtype (86.7%). "
            "UNDER_35 is suppressed due to higher-scoring nature. "
            "BTTS_OVER acceptable cautiously; BOTH_OVER25_BTTS unreliable."
        ),
        "warnings_if": [
            (
                "recommended_market_subtype",
                {"UNDER_35", "BOTH_OVER25_BTTS"},
                "2.Bundesliga: UNDER_35/BOTH_OVER25_BTTS have poor evidence in this goals+volatile league.",
            ),
        ],
    },
    "Premier League": {
        "profile_name": "premier_league_balanced",
        "preferred_types": ["AVOID", "DOUBLE_CHANCE"],
        "preferred_subtypes": ["DOUBLE_CHANCE_1X", "DOUBLE_CHANCE_X2"],
        "suppressed_subtypes": ["OVER_25", "BOTH_OVER25_BTTS"],
        "allowed_subtypes": ["BTTS"],
        "notes": (
            "Premier League is balanced and competitive. "
            "DOUBLE_CHANCE and AVOID are well-supported. "
            "Standalone OVER_25 is weak; BTTS_OVER acceptable only with BTTS subtype. "
            "BOTH_OVER25_BTTS is unreliable."
        ),
        "warnings_if": [
            (
                "recommended_market_subtype",
                {"OVER_25", "BOTH_OVER25_BTTS"},
                "Premier League: OVER_25 standalone and BOTH_OVER25_BTTS have poor evidence.",
            ),
        ],
    },
    "Ligue 1": {
        "profile_name": "ligue1_cautious",
        "preferred_types": ["AVOID", "DOUBLE_CHANCE"],
        "preferred_subtypes": ["DOUBLE_CHANCE_X2", "DOUBLE_CHANCE_1X"],
        "suppressed_subtypes": ["BOTH_OVER25_BTTS", "OVER_25"],
        "allowed_subtypes": [],
        "notes": (
            "Ligue 1 has the lowest overall accuracy (67.4%) due to excess DIRECTION calls. "
            "AVOID and DOUBLE_CHANCE_X2 are most reliable. "
            "DC_1X requires caution. "
            "DIRECTION type triggers a league warning."
        ),
        "warnings_if": [
            (
                "recommended_market_type",
                {"DIRECTION"},
                "Ligue 1: DIRECTION type has historically poor accuracy — consider OBSERVE_ONLY.",
            ),
            (
                "recommended_market_subtype",
                {"OVER_25", "BOTH_OVER25_BTTS"},
                "Ligue 1: goals subtypes have weak evidence in this league.",
            ),
        ],
    },
    "Belgian Pro League": {
        "profile_name": "belgium_balanced_goals",
        "preferred_types": ["AVOID", "DOUBLE_CHANCE", "UNDER"],
        "preferred_subtypes": ["DOUBLE_CHANCE_1X", "DOUBLE_CHANCE_X2", "UNDER_35"],
        "suppressed_subtypes": ["BOTH_OVER25_BTTS"],
        "allowed_subtypes": ["BTTS", "OVER_25"],
        "notes": (
            "Belgian Pro League (Jupiler Pro League) — new/low-sample profile. "
            "DOUBLE_CHANCE and AVOID are cautiously preferred. "
            "Treat goal-combo markets (BOTH_OVER25_BTTS) with caution until "
            "walk-forward evidence is collected."
        ),
        "warnings_if": [
            (
                "recommended_market_subtype",
                {"BOTH_OVER25_BTTS"},
                "Belgian Pro League: new/low-sample profile — "
                "treat goal-combo markets cautiously.",
            ),
        ],
    },
    "Jupiler Pro League": {
        "profile_name": "belgium_balanced_goals",
        "preferred_types": ["AVOID", "DOUBLE_CHANCE", "UNDER"],
        "preferred_subtypes": ["DOUBLE_CHANCE_1X", "DOUBLE_CHANCE_X2", "UNDER_35"],
        "suppressed_subtypes": ["BOTH_OVER25_BTTS"],
        "allowed_subtypes": ["BTTS", "OVER_25"],
        "notes": (
            "Belgian Pro League (Jupiler Pro League) — new/low-sample profile. "
            "DOUBLE_CHANCE and AVOID are cautiously preferred. "
            "Treat goal-combo markets (BOTH_OVER25_BTTS) with caution until "
            "walk-forward evidence is collected."
        ),
        "warnings_if": [
            (
                "recommended_market_subtype",
                {"BOTH_OVER25_BTTS"},
                "Belgian Pro League: new/low-sample profile — "
                "treat goal-combo markets cautiously.",
            ),
        ],
    },
    "Belgium": {
        "profile_name": "belgium_balanced_goals",
        "preferred_types": ["AVOID", "DOUBLE_CHANCE", "UNDER"],
        "preferred_subtypes": ["DOUBLE_CHANCE_1X", "DOUBLE_CHANCE_X2", "UNDER_35"],
        "suppressed_subtypes": ["BOTH_OVER25_BTTS"],
        "allowed_subtypes": ["BTTS", "OVER_25"],
        "notes": (
            "Belgian Pro League (Jupiler Pro League) — new/low-sample profile. "
            "DOUBLE_CHANCE and AVOID are cautiously preferred. "
            "Treat goal-combo markets (BOTH_OVER25_BTTS) with caution until "
            "walk-forward evidence is collected."
        ),
        "warnings_if": [
            (
                "recommended_market_subtype",
                {"BOTH_OVER25_BTTS"},
                "Belgian Pro League: new/low-sample profile — "
                "treat goal-combo markets cautiously.",
            ),
        ],
    },
    "Brasileiro Serie A": {
        "profile_name": "brazil_volatile_control",
        "preferred_types": ["AVOID", "DOUBLE_CHANCE", "UNDER"],
        "preferred_subtypes": ["DOUBLE_CHANCE_1X", "DOUBLE_CHANCE_X2", "UNDER_35"],
        "suppressed_subtypes": ["BOTH_OVER25_BTTS", "BTTS"],
        "allowed_subtypes": ["OVER_25"],
        "notes": (
            "Brasileiro Série A (Campeonato Brasileiro) — custom profile, "
            "treat BTTS/Over-combo markets cautiously until walk-forward evidence "
            "is collected."
        ),
        "warnings_if": [
            (
                "recommended_market_subtype",
                {"BOTH_OVER25_BTTS", "BTTS"},
                "Brasileiro Serie A: custom Brazil profile — "
                "treat BTTS/Over-combo markets cautiously until walk-forward "
                "evidence is collected.",
            ),
        ],
    },
    "Campeonato Brasileiro Serie A": {
        "profile_name": "brazil_volatile_control",
        "preferred_types": ["AVOID", "DOUBLE_CHANCE", "UNDER"],
        "preferred_subtypes": ["DOUBLE_CHANCE_1X", "DOUBLE_CHANCE_X2", "UNDER_35"],
        "suppressed_subtypes": ["BOTH_OVER25_BTTS", "BTTS"],
        "allowed_subtypes": ["OVER_25"],
        "notes": (
            "Brasileiro Série A (Campeonato Brasileiro) — custom profile, "
            "treat BTTS/Over-combo markets cautiously until walk-forward evidence "
            "is collected."
        ),
        "warnings_if": [
            (
                "recommended_market_subtype",
                {"BOTH_OVER25_BTTS", "BTTS"},
                "Brasileiro Serie A: custom Brazil profile — "
                "treat BTTS/Over-combo markets cautiously until walk-forward "
                "evidence is collected.",
            ),
        ],
    },
    "Brasileiro": {
        "profile_name": "brazil_volatile_control",
        "preferred_types": ["AVOID", "DOUBLE_CHANCE", "UNDER"],
        "preferred_subtypes": ["DOUBLE_CHANCE_1X", "DOUBLE_CHANCE_X2", "UNDER_35"],
        "suppressed_subtypes": ["BOTH_OVER25_BTTS", "BTTS"],
        "allowed_subtypes": ["OVER_25"],
        "notes": (
            "Brasileiro Série A (Campeonato Brasileiro) — custom profile, "
            "treat BTTS/Over-combo markets cautiously until walk-forward evidence "
            "is collected."
        ),
        "warnings_if": [
            (
                "recommended_market_subtype",
                {"BOTH_OVER25_BTTS", "BTTS"},
                "Brasileiro Serie A: custom Brazil profile — "
                "treat BTTS/Over-combo markets cautiously until walk-forward "
                "evidence is collected.",
            ),
        ],
    },
    "Brazil": {
        "profile_name": "brazil_volatile_control",
        "preferred_types": ["AVOID", "DOUBLE_CHANCE", "UNDER"],
        "preferred_subtypes": ["DOUBLE_CHANCE_1X", "DOUBLE_CHANCE_X2", "UNDER_35"],
        "suppressed_subtypes": ["BOTH_OVER25_BTTS", "BTTS"],
        "allowed_subtypes": ["OVER_25"],
        "notes": (
            "Brasileiro Série A (Campeonato Brasileiro) — custom profile, "
            "treat BTTS/Over-combo markets cautiously until walk-forward evidence "
            "is collected."
        ),
        "warnings_if": [
            (
                "recommended_market_subtype",
                {"BOTH_OVER25_BTTS", "BTTS"},
                "Brasileiro Serie A: custom Brazil profile — "
                "treat BTTS/Over-combo markets cautiously until walk-forward "
                "evidence is collected.",
            ),
        ],
    },
}

#: Neutral profile returned for unrecognised leagues.
_NEUTRAL_PROFILE: dict[str, Any] = {
    "profile_name": "unknown_league",
    "preferred_types": [],
    "preferred_subtypes": [],
    "suppressed_subtypes": [],
    "allowed_subtypes": [],
    "notes": "No league-specific profile available. Standard cross-league rules apply.",
    "warnings_if": [],
}


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------


def apply_league_market_profile(recommendation: dict, league: str) -> dict:
    """Enrich *recommendation* with league-aware interpretation fields.

    Parameters
    ----------
    recommendation:
        Output dict from ``build_match_features()`` or similar.
        Must contain ``recommended_market_type`` and
        ``recommended_market_subtype`` keys.
    league:
        League name string, e.g. ``"La Liga"``, ``"Eredivisie"``.

    Returns
    -------
    dict
        A **copy** of *recommendation* with the following new keys added:

        ``league_profile``
            Machine-readable profile identifier, e.g. ``"la_liga_control"``.
        ``league_adjusted_strength``
            ``"HIGH"`` / ``"MEDIUM"`` / ``"LOW"`` / ``"SUPPRESSED"`` —
            adjusted reading of the recommendation in this league context.
        ``league_profile_note``
            Human-readable explanation of the league profile.
        ``league_warning_flags``
            Pipe-separated string of active warning messages (empty string
            if none).
        ``league_preferred_subtype``
            Comma-separated string of subtypes this league favours.
        ``league_suppressed_subtype``
            Comma-separated string of subtypes with poor evidence in this
            league.

    Notes
    -----
    Existing fields are **never removed or modified**.
    ``recommended_market_type`` and ``recommended_market_subtype`` are
    untouched — this is a report interpretation layer only.
    """
    profile = LEAGUE_PROFILES.get(league, _NEUTRAL_PROFILE)

    rec_type = str(recommendation.get("recommended_market_type", "") or "")
    rec_subtype = str(recommendation.get("recommended_market_subtype", "") or "")

    # --- determine league_adjusted_strength ---
    adjusted_strength = _compute_adjusted_strength(
        rec_type=rec_type,
        rec_subtype=rec_subtype,
        profile=profile,
        original_strength=recommendation.get("recommendation_strength", ""),
    )

    # --- collect warnings ---
    warnings: list[str] = []
    for field, bad_values, message in profile["warnings_if"]:
        value = str(recommendation.get(field, "") or "")
        if value in bad_values:
            warnings.append(message)

    result = dict(recommendation)  # shallow copy preserves all existing fields

    result["league_profile"] = profile["profile_name"]
    result["league_adjusted_strength"] = adjusted_strength
    result["league_profile_note"] = profile["notes"]
    result["league_warning_flags"] = " | ".join(warnings)
    result["league_preferred_subtype"] = ", ".join(profile["preferred_subtypes"])
    result["league_suppressed_subtype"] = ", ".join(profile["suppressed_subtypes"])

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_adjusted_strength(
    rec_type: str,
    rec_subtype: str,
    profile: dict,
    original_strength: Any,
) -> str:
    """Map original recommendation strength to league-adjusted tier.

    Logic (in priority order):
    1. If subtype is suppressed → SUPPRESSED
    2. If subtype or type is preferred → promote to HIGH (cap at HIGH)
    3. If subtype is explicitly allowed (but not preferred) → keep original or MEDIUM
    4. Otherwise → keep original mapped to tier

    The original_strength values from the system are:
    "STRONG" / "MODERATE" / "LOW" / "VERY LOW" / "" / None
    """
    suppressed = {s.upper() for s in profile.get("suppressed_subtypes", [])}
    preferred_sub = {s.upper() for s in profile.get("preferred_subtypes", [])}
    preferred_type = {t.upper() for t in profile.get("preferred_types", [])}
    allowed_sub = {s.upper() for s in profile.get("allowed_subtypes", [])}

    sub_upper = rec_subtype.upper()
    type_upper = rec_type.upper()

    if sub_upper in suppressed:
        return "SUPPRESSED"

    if sub_upper in preferred_sub or type_upper in preferred_type:
        orig = _normalise_strength(original_strength)
        # Only upgrade; never downgrade a SUPPRESSED (already handled above)
        if orig in ("HIGH", "MEDIUM"):
            return "HIGH"
        return "HIGH"  # promote anything preferred in this league to HIGH

    if sub_upper in allowed_sub:
        orig = _normalise_strength(original_strength)
        return orig if orig != "SUPPRESSED" else "LOW"

    return _normalise_strength(original_strength)


def _normalise_strength(raw: Any) -> str:
    """Convert original recommendation_strength labels to HIGH/MEDIUM/LOW."""
    if raw is None:
        return "LOW"
    s = str(raw).upper().strip()
    if s in ("STRONG",):
        return "HIGH"
    if s in ("MODERATE",):
        return "MEDIUM"
    if s in ("LOW", "VERY LOW", ""):
        return "LOW"
    # Already in target format
    if s in ("HIGH", "MEDIUM", "SUPPRESSED"):
        return s
    return "LOW"
