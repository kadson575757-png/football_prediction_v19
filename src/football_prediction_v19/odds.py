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


def round_optional(value: object, digits: int = 4) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


def value_recommendation(
    odds_home: float | None,
    odds_draw: float | None,
    odds_away: float | None,
    model_probs: dict[str, float],
    assessment: dict[str, Any],
    min_edge: float,
    max_chaos: float,
    min_control: float,
) -> dict[str, object]:
    market = odds_snapshot(odds_home, odds_draw, odds_away, model_probs)
    value_side, value_edge = best_value_side(market["edges"], min_edge)
    no_bets = list(assessment["no_bets"])
    locks = set(assessment["locks"])

    if assessment["control_model_score"] < min_control:
        no_bets.append(f"No value bet: control score below {min_control:g}")
    if assessment["chaos_score"] > max_chaos:
        no_bets.append(f"No value bet: chaos score above {max_chaos:g}")
    if value_side is None:
        no_bets.append(f"No value bet: best model edge below {min_edge:.2%}")
    if value_side == "away" and "away_favorite_degradation" in locks:
        no_bets.append("No away value bet: away-favorite degradation triggered")

    can_recommend = (
        value_side is not None
        and assessment["control_model_score"] >= min_control
        and assessment["chaos_score"] <= max_chaos
        and not (value_side == "away" and "away_favorite_degradation" in locks)
    )

    if can_recommend:
        recommendation = f"Value bet: {LABEL_BY_SIDE[value_side]} 1X2"
        value_pick = LABEL_BY_SIDE[value_side]
    else:
        recommendation = "No bet"
        value_pick = "No Bet"

    return {
        "odds_home": round_optional(market["odds"]["home"]),
        "odds_draw": round_optional(market["odds"]["draw"]),
        "odds_away": round_optional(market["odds"]["away"]),
        "implied_home": round_optional(market["implied"]["home"]),
        "implied_draw": round_optional(market["implied"]["draw"]),
        "implied_away": round_optional(market["implied"]["away"]),
        "fair_home": round_optional(market["fair"]["home"]),
        "fair_draw": round_optional(market["fair"]["draw"]),
        "fair_away": round_optional(market["fair"]["away"]),
        "edge_home": round_optional(market["edges"]["home"]),
        "edge_draw": round_optional(market["edges"]["draw"]),
        "edge_away": round_optional(market["edges"]["away"]),
        "value_pick": value_pick,
        "value_edge": round_optional(value_edge),
        "bet_recommendation": recommendation,
        "no_bet_reasons": list(dict.fromkeys(no_bets)),
    }


def grade_flat_stake_bet(value_pick: str, result: str, odds: float | None, stake: float = 1.0) -> tuple[float, float]:
    if value_pick == "No Bet":
        return 0.0, 0.0
    pick_label = {"Home": "H", "Draw": "D", "Away": "A"}.get(value_pick)
    if pick_label is None or odds is None or pd.isna(odds) or float(odds) <= 1:
        return 0.0, 0.0
    if pick_label == result:
        return float(stake), round(float(odds) - float(stake), 4)
    return float(stake), -float(stake)
