from __future__ import annotations

from typing import Any

ALLOWED_TYPES = {"DIRECTION", "DOUBLE_CHANCE", "BTTS_OVER", "UNDER", "AVOID", "OBSERVE_ONLY"}

#: All allowed values for recommended_market_subtype.
ALLOWED_SUBTYPES: frozenset[str] = frozenset({
    "OVER_25",
    "BTTS",
    "BOTH_OVER25_BTTS",
    "UNDER_25",
    "UNDER_35",
    "DIRECTION_HOME",
    "DIRECTION_AWAY",
    "DOUBLE_CHANCE_1X",
    "DOUBLE_CHANCE_X2",
    "AVOID_VOLATILE",
    "AVOID_LOW_CONTROL",
    "OBSERVE_DATA_WARNING",
    "NONE",
})

GOAL_LEAGUES = {"Eredivisie"}


def _s(value: Any) -> str:
    return "" if value is None else str(value)


def _f(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _score(row: dict[str, Any], base: str) -> float:
    return max(0.0, min(10.0, _f(row.get(f"{base}_score_10", row.get(f"{base}_score")), 0.0)))


def _prob(row: dict[str, Any], side: str) -> float:
    return _f(row.get(f"model_{side}_prob"), 0.0)


def _top_prob(row: dict[str, Any]) -> float:
    likely = _s(row.get("likely_1x2")).lower()
    if likely.startswith("home"):
        return _prob(row, "home")
    if likely.startswith("away"):
        return _prob(row, "away")
    if likely.startswith("draw"):
        return _prob(row, "draw")
    return max(_prob(row, "home"), _prob(row, "draw"), _prob(row, "away"))


def _favorite_side(row: dict[str, Any]) -> str:
    side = _s(row.get("favorite_side"))
    if side:
        return side
    odds_home = _f(row.get("odds_home"), 0.0)
    odds_draw = _f(row.get("odds_draw"), 0.0)
    odds_away = _f(row.get("odds_away"), 0.0)
    if min(odds_home, odds_draw, odds_away) <= 1.0:
        return "NO_CLEAR_FAVORITE"
    lowest = min(odds_home, odds_draw, odds_away)
    if [odds_home, odds_draw, odds_away].count(lowest) > 1:
        return "NO_CLEAR_FAVORITE"
    if odds_home == lowest:
        return "HOME_FAVORITE"
    if odds_away == lowest:
        return "AWAY_FAVORITE"
    return "NO_CLEAR_FAVORITE"


def _favorite_strength(row: dict[str, Any], favorite_side: str) -> str:
    existing = _s(row.get("favorite_strength"))
    if existing:
        return existing
    home_strength = _s(row.get("home_favorite_strength"))
    away_strength = _s(row.get("away_favorite_strength"))
    if favorite_side == "HOME_FAVORITE" and home_strength:
        return home_strength
    if favorite_side == "AWAY_FAVORITE" and away_strength:
        return away_strength
    return "weak_or_no_favorite"


def _is_strong_goals(row: dict[str, Any]) -> bool:
    text = " ".join([
        _s(row.get("goals")),
        _s(row.get("over25_signal")),
        _s(row.get("btts_signal")),
        _s(row.get("probability_profile")),
    ]).lower()
    over25_text = _s(row.get("over25_signal")).lower()
    btts_text   = _s(row.get("btts_signal")).lower()
    # Explicit numeric patterns from older signal formats
    numeric_over = "over2.5" in text or "over 2.5" in text
    # Broader pattern: over25_signal says "over" without negation
    signal_over  = (
        bool(over25_text)
        and "over" in over25_text
        and "not" not in over25_text
        and "unclear" not in over25_text
    )
    # BTTS signal says "btts" without negation
    signal_btts  = (
        bool(btts_text)
        and "btts" in btts_text
        and "no" not in btts_text
        and "not" not in btts_text
        and "unclear" not in btts_text
    )
    return (
        numeric_over
        or signal_over
        or signal_btts
        or bool(row.get("both_over"))
        or bool(row.get("both_btts"))
    )


def _is_under(row: dict[str, Any]) -> bool:
    text = " ".join([_s(row.get("goals")), _s(row.get("under25_signal")), _s(row.get("under35_signal")), _s(row.get("over25_signal"))]).lower()
    return "under" in text or "not-btts" in text


def _weak_btts(row: dict[str, Any]) -> bool:
    text = _s(row.get("btts_signal")).lower()
    return not bool(row.get("both_btts")) and ("no" in text or "weak" in text or "not-btts" in text or "unclear" in text or not text)


def _is_strong_over25(row: dict[str, Any]) -> bool:
    """True when the Over 2.5 signal is distinctly strong (not just 'unclear')."""
    if bool(row.get("both_over")):
        return True
    text = _s(row.get("over25_signal")).lower()
    return bool(text) and "over" in text and "not" not in text and "unclear" not in text


def _is_strong_btts(row: dict[str, Any]) -> bool:
    """True when the BTTS signal is distinctly strong (not 'no'/'unclear')."""
    if bool(row.get("both_btts")):
        return True
    text = _s(row.get("btts_signal")).lower()
    return (
        bool(text)
        and "btts" in text
        and "no" not in text
        and "not" not in text
        and "unclear" not in text
    )


def _btts_over_subtype(row: dict[str, Any]) -> str:
    """Resolve the BTTS_OVER subtype based on which individual signal is strong."""
    strong_o = _is_strong_over25(row)
    strong_b = _is_strong_btts(row)
    if strong_o and strong_b:
        return "BOTH_OVER25_BTTS"
    if strong_o:
        return "OVER_25"
    if strong_b:
        return "BTTS"
    # BTTS_OVER was triggered (e.g. by league or both_over/both_btts flags)
    # but individual text signals are absent — default to OVER_25.
    return "OVER_25"


def _under_subtype(row: dict[str, Any], chaos: float) -> str:
    """Resolve UNDER subtype: UNDER_25 when the under2.5 signal is strong, else UNDER_35."""
    text = _s(row.get("under25_signal")).lower()
    strong_under25 = (
        bool(text)
        and "under" in text
        and "not" not in text
        and "unclear" not in text
        and chaos <= 3.0
    )
    return "UNDER_25" if strong_under25 else "UNDER_35"


def _compute_subtype(
    rec_type: str,
    row: dict[str, Any],
    likely: str,
    read: str,
    avoid_reason: str,
    data_warning: bool,
    chaos: float,
) -> str:
    """Map a finalised rec_type + context signals to a recommended_market_subtype."""
    if rec_type == "BTTS_OVER":
        return _btts_over_subtype(row)

    if rec_type == "UNDER":
        return _under_subtype(row, chaos)

    if rec_type == "DIRECTION":
        if likely.lower().startswith("home"):
            return "DIRECTION_HOME"
        if likely.lower().startswith("away"):
            return "DIRECTION_AWAY"
        return "NONE"

    if rec_type == "DOUBLE_CHANCE":
        read_l = read.lower()
        if "1x" in read_l or "home_or_draw" in read_l:
            return "DOUBLE_CHANCE_1X"
        if "x2" in read_l or "away_or_draw" in read_l:
            return "DOUBLE_CHANCE_X2"
        return "NONE"

    if rec_type == "AVOID":
        reason_l = avoid_reason.lower()
        # disagree / confidence / volatile signals
        if "disagree" in reason_l or "confidence" in reason_l or "warning" in reason_l:
            return "AVOID_VOLATILE"
        # control-based avoid
        return "AVOID_LOW_CONTROL"

    if rec_type == "OBSERVE_ONLY":
        return "OBSERVE_DATA_WARNING" if data_warning else "NONE"

    return "NONE"


def _market_disagree(row: dict[str, Any], likely: str, favorite_side: str) -> bool:
    if favorite_side == "HOME_FAVORITE" and likely == "Away":
        return True
    if favorite_side == "AWAY_FAVORITE" and likely == "Home":
        return True
    return bool(row.get("model_market_disagree", False))


def _double_chance_read(favorite_side: str, likely: str) -> str:
    if favorite_side == "HOME_FAVORITE" or likely == "Home":
        return "home_or_draw_1X"
    if favorite_side == "AWAY_FAVORITE" or likely == "Away":
        return "away_or_draw_X2"
    return "avoid_hard_1x2"


def build_recommended_market(row: dict[str, Any]) -> dict[str, Any]:
    """Build a diagnostic report read from probabilities, control, chaos and form.

    This is not a betting recommendation layer. It does not return odds edge,
    staking, ledger, ROI, paper-test, or profitability fields.
    """
    league = _s(row.get("league"))
    likely = _s(row.get("likely_1x2")) or "Unknown"
    confidence = _s(row.get("confidence")).upper()
    control = _score(row, "control")
    chaos = _score(row, "chaos")
    favorite_side = _favorite_side(row)
    favorite_strength = _favorite_strength(row, favorite_side)
    top_prob = _top_prob(row)
    data_warning = bool(row.get("data_warning"))
    goals_unclear = "unclear" in " ".join([_s(row.get("goals")), _s(row.get("over25_signal")), _s(row.get("btts_signal"))]).lower()
    strong_goals = _is_strong_goals(row)
    under_signal = _is_under(row)
    weak_btts = _weak_btts(row)
    market_disagree = _market_disagree(row, likely, favorite_side)

    rec_type = "OBSERVE_ONLY"
    read = "mixed_signal_observe"
    strength = "LOW"
    risk_note = "diagnostic_only"
    avoid_reason = ""

    if data_warning and not strong_goals:
        rec_type = "AVOID" if likely in {"Home", "Away", "Draw"} else "OBSERVE_ONLY"
        read = "data_warning_reduces_1x2_confidence"
        risk_note = "data_warning"
        avoid_reason = "data warning on main 1X2 read"
    elif control < 1.5 and not strong_goals:
        rec_type = "AVOID"
        read = "too_little_directional_control"
        risk_note = "very_low_control"
        avoid_reason = "control below 1.5 and no strong goals signal"
    elif market_disagree and control < 5.0:
        rec_type = "AVOID"
        read = "model_market_disagreement_low_control"
        risk_note = "disagreement_plus_low_control"
        avoid_reason = "model and market disagree while control is low"
    elif goals_unclear and control < 5.0 and league == "EPL":
        rec_type = "AVOID"
        read = "epl_low_control_unclear_game"
        risk_note = "epl_low_control"
        avoid_reason = "EPL low-control unclear read"
    elif goals_unclear and control < 1.5:
        rec_type = "AVOID"
        read = "unclear_goals_and_very_low_control"
        risk_note = "unclear_low_control"
        avoid_reason = "goals unclear and control very low"
    elif under_signal and chaos <= 3.0 and weak_btts and not row.get("both_over", False):
        rec_type = "UNDER"
        read = "under_profile_low_chaos_weak_btts"
        strength = "MEDIUM" if control >= 2.0 else "LOW"
        risk_note = "under_requires_low_chaos"
    elif strong_goals and (chaos > 3.0 or league in GOAL_LEAGUES or row.get("both_over") or row.get("both_btts")):
        rec_type = "BTTS_OVER"
        read = "goals_profile_preferred_over_hard_1x2"
        strength = "MEDIUM" if chaos <= 5.0 else "LOW"
        if league in GOAL_LEAGUES:
            risk_note = "league_goal_profile_supports_signal"
        else:
            risk_note = "goals_signal_with_control_not_required"
    elif confidence == "NO-CONFIDENCE":
        rec_type = "AVOID"
        read = "no_confidence_on_direction"
        risk_note = "no_confidence"
        avoid_reason = "NO-CONFIDENCE 1X2 read"
    elif confidence == "HIGH" and control >= 5.0 and chaos <= 3.5 and not data_warning and top_prob >= 0.55:
        rec_type = "DIRECTION"
        read = f"{likely.lower()}_direction"
        strength = "HIGH" if control >= 7.0 else "MEDIUM"
        risk_note = "higher_control_lower_chaos_direction"
    elif league == "Ligue 1" and favorite_side == "HOME_FAVORITE" and confidence in {"HIGH", "MEDIUM"} and control >= 5.0 and chaos <= 4.0:
        rec_type = "DIRECTION" if control >= 5.5 else "DOUBLE_CHANCE"
        read = f"{likely.lower()}_direction" if rec_type == "DIRECTION" else _double_chance_read(favorite_side, likely)
        strength = "MEDIUM"
        risk_note = "ligue1_home_favorite_medium_control"
    elif favorite_side in {"HOME_FAVORITE", "AWAY_FAVORITE"} and top_prob >= 0.40 and control < 7.0 and chaos <= 4.0 and confidence in {"LOW", "MEDIUM", "HIGH"}:
        rec_type = "DOUBLE_CHANCE"
        read = _double_chance_read(favorite_side, likely)
        strength = "MEDIUM" if control >= 3.0 or top_prob >= 0.55 else "LOW"
        risk_note = "favorite_direction_but_control_below_hard_1x2"
    elif data_warning and strong_goals:
        rec_type = "OBSERVE_ONLY"
        read = "data_warning_but_goals_signal_interesting"
        risk_note = "data_warning_goals_only"
    elif league in {"La Liga", "EPL"} and control < 5.0:
        rec_type = "OBSERVE_ONLY"
        read = "low_control_prefer_observation"
        risk_note = f"{league.lower().replace(' ', '_')}_low_control"

    preferred_score_family = row.get("score_family") or row.get("preferred_score_family")
    if not preferred_score_family:
        preferred_score_family = {
            "DIRECTION": f"{likely} direction score family",
            "DOUBLE_CHANCE": "1-0, 1-1, 0-1, 2-1 depending side",
            "BTTS_OVER": "2-1, 1-2, 2-2, 3-1",
            "UNDER": "0-0, 1-0, 1-1, 0-1",
            "AVOID": "no stable score-family",
            "OBSERVE_ONLY": "mixed profile",
        }[rec_type]

    subtype = _compute_subtype(
        rec_type=rec_type,
        row=row,
        likely=likely,
        read=read,
        avoid_reason=avoid_reason,
        data_warning=data_warning,
        chaos=chaos,
    )

    return {
        "recommended_market_type":    rec_type,
        "recommended_market_subtype": subtype,
        "recommended_market_read":    read,
        "recommendation_strength":    strength,
        "risk_note":                  risk_note,
        "avoid_reason":               avoid_reason,
        "preferred_score_family":     preferred_score_family,
        "diagnostic_only":            True,
    }
