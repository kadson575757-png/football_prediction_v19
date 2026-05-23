from __future__ import annotations

from typing import Any


HOME_FAVORITE = "HOME_FAVORITE"
AWAY_FAVORITE = "AWAY_FAVORITE"
NO_CLEAR_FAVORITE = "NO_CLEAR_FAVORITE"


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _lowest_favorite(odds_home: float | None, odds_draw: float | None, odds_away: float | None) -> str:
    if odds_home is None or odds_draw is None or odds_away is None:
        return NO_CLEAR_FAVORITE
    if odds_home <= 1.0 or odds_draw <= 1.0 or odds_away <= 1.0:
        return NO_CLEAR_FAVORITE
    lowest = min(odds_home, odds_draw, odds_away)
    if [odds_home, odds_draw, odds_away].count(lowest) > 1:
        return NO_CLEAR_FAVORITE
    if odds_home == lowest:
        return HOME_FAVORITE
    if odds_away == lowest:
        return AWAY_FAVORITE
    return NO_CLEAR_FAVORITE


def _home_strength(odds_home: float | None, favorite_side: str) -> str:
    if favorite_side != HOME_FAVORITE or odds_home is None:
        return "weak_home_fav"
    if odds_home <= 1.50:
        return "very_strong_home_fav"
    if odds_home <= 1.80:
        return "strong_home_fav"
    if odds_home <= 2.20:
        return "medium_home_fav"
    return "weak_home_fav"


def _away_strength(odds_away: float | None, favorite_side: str) -> str:
    if favorite_side != AWAY_FAVORITE or odds_away is None:
        return "weak_away_fav"
    if odds_away <= 1.70:
        return "very_strong_away_fav"
    if odds_away <= 2.20:
        return "strong_away_fav"
    if odds_away <= 2.80:
        return "medium_away_fav"
    return "weak_away_fav"


def _control_bucket(score: float) -> str:
    if score >= 7.0:
        return "HIGH"
    if score >= 5.0:
        return "MEDIUM"
    return "LOW"


def _chaos_bucket(score: float) -> str:
    if score <= 3.0:
        return "LOW"
    if score <= 5.0:
        return "MEDIUM"
    return "HIGH"


def _risk_for_chaos(chaos_bucket: str) -> str:
    if chaos_bucket == "LOW":
        return "low"
    if chaos_bucket == "MEDIUM":
        return "medium"
    return "high"


def _score_family(profile: str) -> str:
    return {
        "clean_home_favorite": "2-0, 2-1, 3-0",
        "home_favorite_but_volatile": "2-1, 3-1, 2-2",
        "clean_away_favorite": "0-2, 1-2, 1-3, 0-3",
        "dangerous_unclear": "volatile; draw/upset/btts possible",
        "low_conviction_calm": "0-0, 1-0, 1-1, 0-1",
    }.get(profile, "use existing model score-family")


def build_control_chaos_profile(row: dict[str, Any]) -> dict[str, Any]:
    """Interpret model control/chaos with market favorite side.

    This is a diagnostic probability interpretation layer only. It does not
    create betting recommendations, paper-test decisions, or ledger signals.
    Scores are expected on the existing 0-10 v1.9 scale.
    """
    odds_home = _as_float(row.get("odds_home"))
    odds_draw = _as_float(row.get("odds_draw"))
    odds_away = _as_float(row.get("odds_away"))
    control_score = _as_float(row.get("control_score"))
    chaos_score = _as_float(row.get("chaos_score"))
    control_score = 0.0 if control_score is None else max(0.0, min(10.0, control_score))
    chaos_score = 0.0 if chaos_score is None else max(0.0, min(10.0, chaos_score))

    favorite_side = _lowest_favorite(odds_home, odds_draw, odds_away)
    control_bucket = _control_bucket(control_score)
    chaos_bucket = _chaos_bucket(chaos_score)

    profile = "standard_uncertain"
    direction_read = "use_model_probabilities_carefully"
    goals_read = "use_form_flags"
    risk_warning = "medium"

    if favorite_side == HOME_FAVORITE and control_bucket == "HIGH" and chaos_bucket == "LOW":
        profile = "clean_home_favorite"
        direction_read = "home_favorite_direction_strong"
        goals_read = "under_3_5_compatible_not_automatic"
        risk_warning = "low"
    elif favorite_side == HOME_FAVORITE and control_bucket == "HIGH" and chaos_bucket in {"MEDIUM", "HIGH"}:
        profile = "home_favorite_but_volatile"
        direction_read = "home_favorite_direction_ok"
        goals_read = "btts_or_upset_risk_elevated"
        risk_warning = "medium_or_high"
    elif favorite_side == AWAY_FAVORITE and control_bucket == "HIGH":
        profile = "clean_away_favorite"
        direction_read = "away_favorite_direction_strong"
        goals_read = "over_2_5_more_interesting"
        risk_warning = _risk_for_chaos(chaos_bucket)
    elif control_bucket == "LOW" and chaos_bucket == "HIGH":
        profile = "dangerous_unclear"
        direction_read = "weak_1x2_conviction"
        goals_read = "btts_draw_upset_risk"
        risk_warning = "high"
    elif control_bucket == "LOW" and chaos_bucket == "LOW":
        profile = "low_conviction_calm"
        direction_read = "weak_direction"
        goals_read = "unclear_or_low_event"
        risk_warning = "medium"

    return {
        "favorite_side": favorite_side,
        "home_favorite_strength": _home_strength(odds_home, favorite_side),
        "away_favorite_strength": _away_strength(odds_away, favorite_side),
        "control_score": round(control_score, 2),
        "chaos_score": round(chaos_score, 2),
        "control_bucket": control_bucket,
        "chaos_bucket": chaos_bucket,
        "probability_profile": profile,
        "direction_read": direction_read,
        "goals_read": goals_read,
        "risk_warning": risk_warning,
        "score_family": _score_family(profile),
        "is_betting_recommendation": False,
        "bet_recommendation": None,
        "diagnostic_only": True,
        "form_flags": {
            "both_over": bool(row.get("both_over", False)),
            "both_btts": bool(row.get("both_btts", False)),
            "home_gf_high": bool(row.get("home_gf_high", False)),
            "form_mismatch_H": bool(row.get("form_mismatch_H", False)),
        },
        "model_probabilities": {
            "home": _as_float(row.get("model_home_prob")),
            "draw": _as_float(row.get("model_draw_prob")),
            "away": _as_float(row.get("model_away_prob")),
        },
        "likely_1x2": row.get("likely_1x2"),
    }
