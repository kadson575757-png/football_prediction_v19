from __future__ import annotations

from typing import Any

import pandas as pd

SIDES = ("home", "draw", "away")
LABEL_BY_SIDE = {"home": "Home", "draw": "Draw", "away": "Away"}
SIDE_BY_LABEL = {"H": "home", "D": "draw", "A": "away"}
MODEL_KEY_BY_SIDE = {"home": "H", "draw": "D", "away": "A"}


def implied_probability(decimal_odds: float | int | None) -> float | None:
    if decimal_odds is None or pd.isna(decimal_odds) or float(decimal_odds) <= 1:
        return None
    return 1.0 / float(decimal_odds)


def implied_probabilities(odds: dict[str, float | None]) -> dict[str, float | None]:
    return {side: implied_probability(odds.get(side)) for side in SIDES}


def bookmaker_overround(odds: dict[str, float | None]) -> float | None:
    implied = implied_probabilities(odds)
    if any(value is None for value in implied.values()):
        return None
    return float(sum(value for value in implied.values() if value is not None) - 1.0)


def fair_probabilities(odds: dict[str, float | None]) -> dict[str, float | None]:
    implied = implied_probabilities(odds)
    if any(value is None for value in implied.values()):
        return {side: None for side in SIDES}
    total = sum(value for value in implied.values() if value is not None)
    if total <= 0:
        return {side: None for side in SIDES}
    return {side: float(implied[side] / total) for side in SIDES if implied[side] is not None}


def model_edges(model_probs: dict[str, float], fair_probs: dict[str, float | None]) -> dict[str, float | None]:
    edges: dict[str, float | None] = {}
    for side in SIDES:
        fair = fair_probs.get(side)
        if fair is None:
            edges[side] = None
        else:
            edges[side] = float(model_probs[MODEL_KEY_BY_SIDE[side]] - fair)
    return edges


def odds_snapshot(
    odds_home: float | None,
    odds_draw: float | None,
    odds_away: float | None,
    model_probs: dict[str, float],
) -> dict[str, Any]:
    odds = {"home": odds_home, "draw": odds_draw, "away": odds_away}
    implied = implied_probabilities(odds)
    fair = fair_probabilities(odds)
    edges = model_edges(model_probs, fair)
    return {
        "odds": odds,
        "implied": implied,
        "overround": bookmaker_overround(odds),
        "fair": fair,
        "edges": edges,
    }


def best_value_side(edges: dict[str, float | None], min_edge: float) -> tuple[str | None, float | None]:
    valid = {side: edge for side, edge in edges.items() if edge is not None}
    if not valid:
        return None, None
    side, edge = max(valid.items(), key=lambda item: item[1])
    if edge < min_edge:
        return None, edge
    return side, edge
