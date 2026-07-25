"""Rule-based match profiles derived only from model outputs."""

from __future__ import annotations


def build_match_profile(primary: dict[str, float], goal: dict) -> dict:
    total_xg = goal["expected_home_goals"] + goal["expected_away_goals"]
    spread = abs(primary["HOME"] - primary["AWAY"])
    top = max(primary, key=primary.get)
    if total_xg >= 3.2 and spread < 0.12:
        profile = "OPEN_HIGH_SCORING"
    elif total_xg >= 3.0 and spread >= 0.22:
        profile = "ONE_SIDED_HIGH_SCORING"
    elif primary["DRAW"] >= 0.32 and total_xg < 2.35:
        profile = "BALANCED_LOW_SCORING"
    elif spread < 0.09 and total_xg < 3.0:
        profile = "BALANCED_MODERATE"
    elif top == "HOME" and primary["HOME"] >= 0.48:
        profile = "HOME_CONTROL"
    elif top == "AWAY" and primary["AWAY"] >= 0.48:
        profile = "AWAY_CONTROL"
    elif total_xg >= 3.0:
        profile = "HIGH_VARIANCE"
    else:
        profile = "UNCERTAIN_MIXED_SIGNALS"
    likely_game_state = (
        "HOME_LEADING" if top == "HOME" and primary_edge(primary) >= 0.05
        else "AWAY_LEADING" if top == "AWAY" and primary_edge(primary) >= 0.05
        else "LEVEL_OR_UNCERTAIN"
    )
    scoring_environment = "LOW" if total_xg < 2.3 else "HIGH" if total_xg >= 3.0 else "MODERATE"
    balance_level = "HIGH" if spread < 0.08 else "MEDIUM" if spread < 0.18 else "LOW"
    variance_level = "HIGH" if total_xg >= 3.0 else "MEDIUM" if total_xg >= 2.3 else "LOW"
    comeback_risk = "HIGH" if spread < 0.12 and total_xg >= 2.7 else "MODERATE"
    late_goal_risk = "HIGH" if total_xg >= 2.8 else "MODERATE" if total_xg >= 2.2 else "LOW"
    return {
        "main_profile": profile,
        "likely_game_state": likely_game_state,
        "scoring_environment": scoring_environment,
        "balance_level": balance_level,
        "variance_level": variance_level,
        "comeback_risk": comeback_risk,
        "late_goal_risk": late_goal_risk,
        "profile_rule_audit": [
            {
                "profile_rule_name": "likely_game_state",
                "input_values": {"top_outcome": top, "primary_probability_edge": primary_edge(primary)},
                "thresholds": {"minimum_directional_edge": 0.05},
                "resulting_label": likely_game_state,
            },
            {
                "profile_rule_name": "balance_level",
                "input_values": {"home_away_probability_spread": spread},
                "thresholds": {"high_below": 0.08, "medium_below": 0.18},
                "resulting_label": balance_level,
            },
            {
                "profile_rule_name": "variance_and_goal_timing",
                "input_values": {"expected_total_goals": total_xg, "home_away_probability_spread": spread},
                "thresholds": {
                    "high_variance_total_goals": 3.0,
                    "high_comeback_max_spread": 0.12,
                    "high_comeback_min_total_goals": 2.7,
                    "high_late_goal_total_goals": 2.8,
                },
                "resulting_label": {
                    "variance_level": variance_level,
                    "comeback_risk": comeback_risk,
                    "late_goal_risk": late_goal_risk,
                },
            },
        ],
    }


def primary_edge(primary: dict[str, float]) -> float:
    ranked = sorted(primary.values(), reverse=True)
    return ranked[0] - ranked[1]
