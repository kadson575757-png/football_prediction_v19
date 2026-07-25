"""Evidence-bound explanations for unified prematch outputs."""

from __future__ import annotations


def _factor(name: str, value: float, direction: str, text: str, quality: str) -> dict:
    return {
        "feature_name": name,
        "direction": direction,
        "magnitude": abs(float(value)),
        "human_readable_explanation": text,
        "source_quality": quality,
    }


EDGE_THRESHOLD = 0.10
BALANCE_THRESHOLD = 0.08


def build_explanations(
    features: dict,
    goal: dict,
    quality: dict,
    primary: dict[str, float] | None = None,
    comparison: dict | None = None,
) -> dict:
    source_quality = quality["quality_tier"]
    home_ppg = float(features.get("home_venue_points_per_match") or 0.0)
    away_ppg = float(features.get("away_venue_points_per_match") or 0.0)
    home_form = float(features.get("home_last5_points") or 0.0)
    away_form = float(features.get("away_last5_points") or 0.0)
    total_xg = goal["expected_home_goals"] + goal["expected_away_goals"]
    directional = [
        ("venue_ppg_edge", home_ppg - away_ppg, "venue points rate"),
        ("recent_points_edge", home_form - away_form, "recent points rate"),
    ]
    home_factors, away_factors, draw_factors = [], [], []
    for name, edge, label in directional:
        if edge > EDGE_THRESHOLD:
            home_factors.append(_factor(name, edge, "HOME", f"Home {label} exceeds the away {label}.", source_quality))
        elif edge < -EDGE_THRESHOLD:
            away_factors.append(_factor(name, edge, "AWAY", f"Away {label} exceeds the home {label}.", source_quality))
        elif abs(edge) <= BALANCE_THRESHOLD:
            draw_factors.append(_factor(name, edge, "DRAW", f"The teams have similar {label}s.", source_quality))
    quality_factors = []
    minimum_history = int(quality["minimum_team_history"])
    if minimum_history >= 10:
        quality_factors.append(_factor(
            "established_history", minimum_history, "QUALITY",
            f"Both teams have at least {minimum_history} prior matches in the local history.", source_quality,
        ))
    if quality.get("venue_history_ready"):
        quality_factors.append(_factor("venue_history_ready", 1, "QUALITY", "Venue-specific history is available for both teams.", source_quality))
    if quality.get("asof_clean", True):
        quality_factors.append(_factor("asof_clean", 1, "QUALITY", "All historical inputs precede the target match.", source_quality))
    uncertainty_factors = []
    if minimum_history < 5:
        uncertainty_factors.append(_factor("low_history", minimum_history, "UNCERTAINTY", "One or both teams have limited prior history.", source_quality))
    if quality.get("fallback_used"):
        uncertainty_factors.append(_factor("fallback_used", 1, "UNCERTAINTY", "One or more rolling features use a documented fallback.", source_quality))
    if primary:
        ranked = sorted(primary.items(), key=lambda item: item[1], reverse=True)
        edge = ranked[0][1] - ranked[1][1]
        if edge < 0.08:
            uncertainty_factors.append(_factor(
                "primary_probability_edge", edge, "UNCERTAINTY",
                f"The primary {ranked[0][0]} advantage over {ranked[1][0]} is only {edge:.2%}.", source_quality,
            ))
    if comparison and comparison.get("conflict_level") in {"MEDIUM", "HIGH"}:
        uncertainty_factors.append(_factor("model_conflict", comparison["maximum_probability_difference"], "UNCERTAINTY", "The primary and supporting models show a material conflict.", source_quality))
    return {
        "top_home_factors": home_factors[:5],
        "top_away_factors": away_factors[:5],
        "top_draw_factors": draw_factors[:5],
        "top_goal_factors": [
            _factor("expected_goal_total", total_xg, "GOALS", f"The supporting goal model expects {total_xg:.2f} total goals.", source_quality),
        ],
        "quality_factors": quality_factors[:5],
        "uncertainty_factors": uncertainty_factors[:5],
    }
