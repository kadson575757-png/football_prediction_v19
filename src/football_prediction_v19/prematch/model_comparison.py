"""Compare model views without mixing their probabilities."""

from __future__ import annotations


def compare_models(primary: dict[str, float], goal_view: dict[str, float]) -> dict:
    primary_top = max(primary, key=primary.get)
    goal_top = max(goal_view, key=goal_view.get)
    primary_ranked = sorted(primary.values(), reverse=True)
    goal_ranked = sorted(goal_view.values(), reverse=True)
    primary_edge = primary_ranked[0] - primary_ranked[1]
    goal_edge = goal_ranked[0] - goal_ranked[1]
    maximum_difference = max(abs(primary[key] - goal_view[key]) for key in primary)
    if primary_top == goal_top:
        conflict = "NONE" if maximum_difference < 0.05 else "LOW" if maximum_difference < 0.15 else "MEDIUM"
    elif primary_edge < 0.08 and goal_edge < 0.08:
        conflict = "MEDIUM"
    else:
        conflict = "HIGH"
    return {
        "primary_top_outcome": primary_top,
        "goal_model_top_outcome": goal_top,
        "supporting_top_outcome": goal_top,
        "top_outcome_agreement": primary_top == goal_top,
        "same_top_outcome": primary_top == goal_top,
        "primary_probabilities": dict(primary),
        "goal_model_probabilities": dict(goal_view),
        "maximum_probability_difference": maximum_difference,
        "conflict_level": conflict,
        "interpretation": (
            f"The goal model supports the primary direction; the maximum probability difference is {maximum_difference:.1%}."
            if primary_top == goal_top
            else f"The models disagree ({conflict} conflict); the primary winner output remains authoritative."
        ),
        "conflict_thresholds": {
            "same_top_none_below": 0.05,
            "same_top_low_below": 0.15,
            "different_top_low_edge_below": 0.08,
        },
        "probability_mixing_applied": False,
    }
