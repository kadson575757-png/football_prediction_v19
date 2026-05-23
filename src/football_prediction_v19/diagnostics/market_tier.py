# -*- coding: utf-8 -*-
"""Diagnostic market tier classifier.

REPORT INTERPRETATION LAYER ONLY.
- Does not change recommended_market_type or recommended_market_subtype.
- Does not alter model probabilities.
- No betting rules, no ROI, no staking.
- Adds new fields only; never removes existing ones.

Tiers are derived from TRUE walk-forward aggregate results across 6 leagues
and 19 season-league combinations.  Evidence basis: 4,089+ evaluatable matches.

Public API
----------
build_market_tier(recommendation: dict) -> dict
    Adds 4 new fields to *recommendation* and returns the augmented dict.

New fields added
----------------
market_tier        : A_TIER | B_TIER | C_TIER | DOWNGRADE | HARD_NO_GO | OBSERVE_ONLY
market_tier_score  : int 0-100  (higher = stronger diagnostic signal)
market_tier_reason : short human-readable reason string
market_tier_flags  : pipe-separated diagnostic flag string (may be empty)
"""

from __future__ import annotations

__all__ = ["build_market_tier", "MARKET_TIERS"]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MARKET_TIERS = (
    "A_TIER",
    "B_TIER",
    "C_TIER",
    "DOWNGRADE",
    "HARD_NO_GO",
    "OBSERVE_ONLY",
)

# Subtypes that qualify for A-Tier (walk-forward baseline >=75%)
_A_TIER_SUBTYPES: frozenset[str] = frozenset(
    {"UNDER_35", "DOUBLE_CHANCE_1X", "DOUBLE_CHANCE_X2"}
)

# Subtypes that are unconditional HARD_NO_GO
_HARD_NOGO_SUBTYPES: frozenset[str] = frozenset({"BOTH_OVER25_BTTS"})

# Subtypes that are DOWNGRADE by default unless in a goal-friendly context
_DOWNGRADE_SUBTYPES: frozenset[str] = frozenset({"BTTS"})

# Goal-friendly league profiles (OVER_25 / BTTS acceptable evidence)
_GOAL_FRIENDLY_PROFILES: frozenset[str] = frozenset(
    {"eredivisie_goals", "bundesliga2_goals_volatile"}
)

# Leagues where OVER_25 is not automatically downgraded
# (Premier League added per walk-forward spec; Eredivisie and 2.Bundesliga via profile)
_OVER25_OK_LEAGUES: frozenset[str] = frozenset(
    {"Eredivisie", "2. Bundesliga", "Premier League", "EPL"}
)

# chaos_score_10 threshold for A-Tier eligibility
_CHAOS_THRESHOLD_A: float = 6.0

# Minimum chaos penalty threshold
_CHAOS_HIGH: float = 6.0
_CHAOS_LOW: float = 4.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _str(val: object) -> str:
    """Safe str conversion; None/float NaN → ''."""
    if val is None:
        return ""
    s = str(val)
    return "" if s.lower() in ("nan", "none", "") else s.strip()


def _upper(val: object) -> str:
    return _str(val).upper()


def _split_list(raw: object) -> frozenset[str]:
    """Parse a comma-separated string of subtypes into a frozenset of uppercase tokens."""
    s = _str(raw)
    if not s:
        return frozenset()
    return frozenset(t.strip().upper() for t in s.split(",") if t.strip())


def _chaos(rec: dict) -> float | None:
    """Return chaos_score_10 as float, or None if unavailable/invalid."""
    raw = rec.get("chaos_score_10")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _compute_score(
    *,
    strength: str,
    subtype: str,
    pref_subtypes: frozenset[str],
    supp_subtypes: frozenset[str],
    has_warning: bool,
    chaos: float | None,
    confidence: str,
    data_warning: bool,
    mtype: str,
) -> int:
    """Compute a 0-100 diagnostic score (higher = stronger signal)."""
    score = 50

    # League-adjusted strength contribution
    if strength == "HIGH":
        score += 20
    elif strength == "MEDIUM":
        score += 5
    elif strength == "LOW":
        score -= 5
    elif strength == "SUPPRESSED":
        score -= 15

    # Preferred/suppressed subtype
    sub_up = subtype.upper()
    if sub_up in pref_subtypes:
        score += 10
    if sub_up in supp_subtypes:
        score -= 15

    # A-Tier subtypes get an extra boost
    if sub_up in _A_TIER_SUBTYPES:
        score += 8

    # Warning flags penalty
    if has_warning:
        score -= 15

    # Chaos contribution
    if chaos is not None:
        if chaos < _CHAOS_LOW:
            score += 5
        elif chaos > _CHAOS_HIGH:
            score -= 10

    # Confidence / data flags
    if confidence == "NO-CONFIDENCE":
        score -= 10
    if data_warning:
        score -= 8

    # HARD_NO_GO subtypes drag score to floor
    if sub_up in _HARD_NOGO_SUBTYPES:
        score = min(score, 20)

    return max(0, min(100, score))


# ---------------------------------------------------------------------------
# Main classifier
# ---------------------------------------------------------------------------

def build_market_tier(recommendation: dict) -> dict:  # noqa: C901
    """Add market tier fields to *recommendation* without modifying existing fields.

    Parameters
    ----------
    recommendation:
        Dict produced by ``build_recommended_market`` and optionally enriched
        by ``apply_league_market_profile``.  All keys are optional; the
        function degrades gracefully to OBSERVE_ONLY / C_TIER if data is thin.

    Returns
    -------
    dict
        Shallow copy of *recommendation* with 4 new keys added:
        ``market_tier``, ``market_tier_score``, ``market_tier_reason``,
        ``market_tier_flags``.
    """
    # ── Extract fields ───────────────────────────────────────────────────────
    mtype      = _upper(recommendation.get("recommended_market_type"))
    subtype    = _upper(recommendation.get("recommended_market_subtype"))
    strength   = _upper(recommendation.get("league_adjusted_strength"))
    profile    = _str(recommendation.get("league_profile"))
    warning    = _str(recommendation.get("league_warning_flags"))
    league     = _str(recommendation.get("league"))
    confidence = _upper(recommendation.get("confidence"))
    has_warning: bool = len(warning) > 0

    pref_subtypes = _split_list(recommendation.get("league_preferred_subtype"))
    supp_subtypes = _split_list(recommendation.get("league_suppressed_subtype"))

    chaos = _chaos(recommendation)
    data_warning: bool = bool(recommendation.get("data_warning", False))

    flags: list[str] = []

    # ── Decision tree (priority order) ──────────────────────────────────────

    # 1. OBSERVE_ONLY  — existing market type or genuinely missing data
    if mtype == "OBSERVE_ONLY":
        tier = "OBSERVE_ONLY"
        reason = "Market type is OBSERVE_ONLY — insufficient signal for classification."
        flags.append("observe_only_type")

    elif (data_warning and confidence == "NO-CONFIDENCE") or (
        recommendation.get("home_stats_n") is not None
        and int(recommendation.get("home_stats_n", 5)) < 2
    ):
        tier = "OBSERVE_ONLY"
        reason = "Data warning combined with NO-CONFIDENCE — no usable history."
        flags.append("data_warning")
        flags.append("no_confidence")

    # 2. HARD_NO_GO
    elif subtype in _HARD_NOGO_SUBTYPES:
        tier = "HARD_NO_GO"
        reason = f"Subtype {subtype} has consistently poor walk-forward evidence across all leagues."
        flags.append(f"hard_nogo_subtype:{subtype}")

    elif strength == "SUPPRESSED" and has_warning:
        tier = "HARD_NO_GO"
        reason = "SUPPRESSED league_adjusted_strength combined with active warning flag."
        flags.append("suppressed_strength")
        flags.append("warning_flag")

    elif _is_ligue1_direction(league, profile, mtype, subtype):
        tier = "HARD_NO_GO"
        reason = "Ligue 1 DIRECTION type has historically poor accuracy (walk-forward evidence)."
        flags.append("ligue1_direction")

    elif data_warning and confidence == "NO-CONFIDENCE":
        tier = "HARD_NO_GO"
        reason = "Severe data warning with NO-CONFIDENCE: outcome undetermined."
        flags.append("data_warning")
        flags.append("no_confidence")

    # 3. A_TIER
    elif _qualifies_a_tier(
        strength=strength,
        subtype=subtype,
        has_warning=has_warning,
        chaos=chaos,
        league=league,
        profile=profile,
        mtype=mtype,
    ):
        tier = "A_TIER"
        reason = (
            f"HIGH adjusted strength + preferred subtype ({subtype}) "
            f"+ clean signal (no warning, chaos within range)."
        )
        flags.append("high_strength")
        flags.append(f"preferred_subtype:{subtype}")
        if chaos is not None and chaos < _CHAOS_LOW:
            flags.append("chaos_low")

    # 4. B_TIER
    elif _qualifies_b_tier(
        strength=strength,
        subtype=subtype,
        has_warning=has_warning,
        profile=profile,
        league=league,
    ):
        tier = "B_TIER"
        reason = (
            f"Adjusted strength {strength or 'unknown'}, no warning, "
            f"subtype not suppressed."
        )
        flags.append(f"strength:{strength}")
        if subtype in pref_subtypes:
            flags.append(f"preferred_subtype:{subtype}")

    # 5. DOWNGRADE
    elif _qualifies_downgrade(
        strength=strength,
        subtype=subtype,
        has_warning=has_warning,
        profile=profile,
        league=league,
    ):
        tier = "DOWNGRADE"
        reason = _downgrade_reason(
            strength=strength,
            subtype=subtype,
            has_warning=has_warning,
            league=league,
        )
        if has_warning:
            flags.append("warning_flag")
        if subtype in _DOWNGRADE_SUBTYPES:
            flags.append(f"downgrade_subtype:{subtype}")
        if subtype == "OVER_25" and league not in _OVER25_OK_LEAGUES and not _is_goal_friendly(profile):
            flags.append("over25_non_goal_friendly_league")

    # 6. C_TIER  — everything else
    else:
        tier = "C_TIER"
        reason = "Neutral conviction — no strong signal in either direction."
        if strength:
            flags.append(f"strength:{strength}")
        if has_warning:
            flags.append("mild_warning")

    # ── Score ────────────────────────────────────────────────────────────────
    score = _compute_score(
        strength=strength,
        subtype=subtype,
        pref_subtypes=pref_subtypes,
        supp_subtypes=supp_subtypes,
        has_warning=has_warning,
        chaos=chaos,
        confidence=confidence,
        data_warning=data_warning,
        mtype=mtype,
    )

    # Override score bounds for extreme tiers to maintain consistency
    if tier == "HARD_NO_GO":
        score = min(score, 24)
    elif tier == "OBSERVE_ONLY":
        score = min(score, 20)
    elif tier == "DOWNGRADE":
        score = max(15, min(score, 44))
    elif tier == "C_TIER":
        score = max(25, min(score, 59))
    elif tier == "B_TIER":
        score = max(45, min(score, 74))
    elif tier == "A_TIER":
        score = max(65, min(score, 100))

    # ── Assemble result ───────────────────────────────────────────────────────
    result = dict(recommendation)  # shallow copy — all existing fields preserved
    result["market_tier"]        = tier
    result["market_tier_score"]  = score
    result["market_tier_reason"] = reason
    result["market_tier_flags"]  = " | ".join(flags)
    return result


# ---------------------------------------------------------------------------
# Tier predicate helpers
# ---------------------------------------------------------------------------

def _is_goal_friendly(profile: str) -> bool:
    return profile.lower() in _GOAL_FRIENDLY_PROFILES


def _is_ligue1_direction(
    league: str, profile: str, mtype: str, subtype: str
) -> bool:
    """True when this is a Ligue 1 DIRECTION market — historically very poor."""
    is_ligue1 = "ligue 1" in league.lower() or profile == "ligue1_cautious"
    is_direction = mtype == "DIRECTION" or subtype.startswith("DIRECTION")
    return is_ligue1 and is_direction


def _qualifies_a_tier(
    *,
    strength: str,
    subtype: str,
    has_warning: bool,
    chaos: float | None,
    league: str,
    profile: str,
    mtype: str,
) -> bool:
    if strength != "HIGH":
        return False
    if has_warning:
        return False
    if subtype not in _A_TIER_SUBTYPES:
        return False
    if chaos is not None and chaos >= _CHAOS_THRESHOLD_A:
        return False
    # Ligue 1 is weaker even for A-Tier subtypes — excluded from A-Tier
    if "ligue 1" in league.lower() or profile == "ligue1_cautious":
        return False
    return True


def _qualifies_b_tier(
    *,
    strength: str,
    subtype: str,
    has_warning: bool,
    profile: str,
    league: str = "",
) -> bool:
    if strength not in ("HIGH", "MEDIUM"):
        return False
    if has_warning:
        return False
    if subtype in _HARD_NOGO_SUBTYPES:
        return False
    if subtype in _DOWNGRADE_SUBTYPES:
        # BTTS is only B-Tier in goal-friendly profiles
        return _is_goal_friendly(profile)
    if subtype == "OVER_25":
        # OVER_25 is B-Tier only in goal-friendly context
        return league in _OVER25_OK_LEAGUES or _is_goal_friendly(profile)
    return True


def _qualifies_downgrade(
    *,
    strength: str,
    subtype: str,
    has_warning: bool,
    profile: str,
    league: str,
) -> bool:
    if has_warning:
        return True
    if subtype in _DOWNGRADE_SUBTYPES:
        return True
    if subtype == "OVER_25":
        is_ok = league in _OVER25_OK_LEAGUES or _is_goal_friendly(profile)
        if not is_ok:
            return True
    if strength in ("MEDIUM", "LOW") and _is_goal_friendly(profile):
        # Goals profile + non-HIGH strength = downgrade
        return True
    if strength == "SUPPRESSED":
        # SUPPRESSED without warning is still a downgrade
        return True
    return False


def _downgrade_reason(
    *,
    strength: str,
    subtype: str,
    has_warning: bool,
    league: str,
) -> str:
    parts: list[str] = []
    if has_warning:
        parts.append("active league warning flag")
    if subtype in _DOWNGRADE_SUBTYPES:
        parts.append(f"{subtype} has weak cross-league evidence")
    if subtype == "OVER_25" and league not in _OVER25_OK_LEAGUES:
        parts.append(f"OVER_25 in {league or 'unknown league'} is outside goal-friendly context")
    if strength == "SUPPRESSED":
        parts.append("league_adjusted_strength is SUPPRESSED")
    if not parts:
        parts.append("low conviction or goals-profile volatility")
    return "; ".join(parts).capitalize() + "."
