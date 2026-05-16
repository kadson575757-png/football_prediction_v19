from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

LABELS = {"H": "Home", "D": "Draw", "A": "Away"}


def _clip(value: float, lo: float, hi: float) -> float:
    if pd.isna(value):
        return float(lo)
    return float(max(lo, min(hi, value)))


def _n(row: pd.Series | dict[str, Any], key: str, default: float = np.nan) -> float:
    try:
        val = row.get(key, default) if isinstance(row, dict) else row.get(key, default)
        return float(val) if pd.notna(val) else default
    except Exception:
        return default


def team_distress_index(row: pd.Series, side: str) -> int:
    """TDI 0-4: a compact distress signal for weak form / defensive instability.

    This is intentionally transparent and editable. Tune thresholds after backtesting.
    """
    ppg = _n(row, f"{side}_w5_ppg")
    xga = _n(row, f"{side}_w5_xga")
    xgf = _n(row, f"{side}_w5_xgf")
    gd = _n(row, f"{side}_w5_goaldiff")
    tdi = 0
    tdi += int(pd.notna(ppg) and ppg < 1.00)
    tdi += int(pd.notna(xga) and xga > 1.60)
    tdi += int(pd.notna(xgf) and xgf < 1.05)
    tdi += int(pd.notna(gd) and gd < -0.60)
    return int(tdi)


def chaos_score(row: pd.Series, probs: dict[str, float]) -> float:
    ordered = sorted([float(probs.get("H", 0)), float(probs.get("D", 0)), float(probs.get("A", 0))], reverse=True)
    prob_edge = ordered[0] - ordered[1] if len(ordered) >= 2 else 0.0
    home_tdi = team_distress_index(row, "home")
    away_tdi = team_distress_index(row, "away")
    expected_total = _n(row, "expected_total_xg_w5", np.nan)
    market_overround = _n(row, "market_overround", 0.05)
    odds_moves = [abs(_n(row, f"market_move_{s}", 0.0)) for s in ["home", "draw", "away"]]
    market_volatility = max([v for v in odds_moves if pd.notna(v)] or [0.0])

    score = 2.0
    score += (1.0 - _clip(prob_edge / 0.18, 0, 1)) * 3.0
    score += min(home_tdi + away_tdi, 6) * 0.55
    if pd.notna(expected_total) and expected_total > 3.0:
        score += 0.8
    if market_overround > 0.08:
        score += 0.5
    if market_volatility > 0.08:
        score += 1.0
    return round(_clip(score, 0, 10), 2)


def control_model_score(row: pd.Series, probs: dict[str, float], top_label: str, chaos: float) -> float:
    ordered = sorted(probs.values(), reverse=True)
    top_prob = ordered[0]
    edge = ordered[0] - ordered[1] if len(ordered) >= 2 else 0.0
    xg_edge = _n(row, "edge_w5_xgdiff", 0.0)
    ppg_edge = _n(row, "edge_w5_ppg", 0.0)

    if top_label == "A":
        xg_edge = -xg_edge
        ppg_edge = -ppg_edge
    elif top_label == "D":
        xg_edge = -abs(xg_edge)
        ppg_edge = -abs(ppg_edge)

    score = 3.0
    score += _clip((top_prob - 0.34) / 0.20, 0, 1) * 2.0
    score += _clip(edge / 0.15, 0, 1) * 2.0
    score += _clip(xg_edge / 0.60, -1, 1) * 1.2
    score += _clip(ppg_edge / 1.20, -1, 1) * 0.8
    score += (1.0 - chaos / 10.0) * 1.0
    return round(_clip(score, 0, 10), 2)


def _market_value(row: pd.Series, label: str, prob: float) -> dict[str, Any]:
    side = {"H": "home", "D": "draw", "A": "away"}[label]
    odds = _n(row, f"odds_{side}", np.nan)
    if pd.isna(odds) or odds <= 1:
        return {"odds": None, "implied_prob": None, "edge": None, "value": None}
    implied = 1.0 / odds
    edge = prob - implied
    return {"odds": odds, "implied_prob": implied, "edge": edge, "value": edge > 0.03}


def score_family(row: pd.Series, probs: dict[str, float]) -> list[str]:
    home_xg = _n(row, "home_w5_xgf", 1.25)
    away_xg = _n(row, "away_w5_xgf", 1.10)
    # Blend attack and opponent defensive concessions.
    home_est = np.nanmean([home_xg, _n(row, "away_w5_xga", 1.20)])
    away_est = np.nanmean([away_xg, _n(row, "home_w5_xga", 1.20)])
    if pd.isna(home_est): home_est = 1.2
    if pd.isna(away_est): away_est = 1.1

    scenarios = []
    if probs.get("H", 0) >= max(probs.get("D", 0), probs.get("A", 0)):
        scenarios.extend([f"{round(home_est):.0f}-{max(0, round(away_est)-1):.0f}", "2-1", "1-0"])
    elif probs.get("A", 0) >= max(probs.get("D", 0), probs.get("H", 0)):
        scenarios.extend([f"{max(0, round(home_est)-1):.0f}-{round(away_est):.0f}", "1-2", "0-1"])
    else:
        scenarios.extend(["1-1", "0-0", "2-2"])
    # de-duplicate preserving order
    out = []
    for s in scenarios:
        if s not in out:
            out.append(s)
    return out[:3]


def assess_prediction(row: pd.Series | dict[str, Any], probs: dict[str, float]) -> dict[str, Any]:
    if isinstance(row, dict):
        row = pd.Series(row)
    probs = {k: float(v) for k, v in probs.items()}
    top_label = max(probs, key=probs.get)
    ordered = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
    top_prob = ordered[0][1]
    second_prob = ordered[1][1] if len(ordered) > 1 else 0.0
    prob_edge = top_prob - second_prob

    home_tdi = team_distress_index(row, "home")
    away_tdi = team_distress_index(row, "away")
    chaos = chaos_score(row, probs)
    control = control_model_score(row, probs, top_label, chaos)
    expected_total = _n(row, "expected_total_xg_w5", np.nan)

    no_bets: list[str] = []
    locks: list[str] = []
    recommendations: list[dict[str, Any]] = []

    if control < 7.0:
        no_bets.append("1X2 hard tip locked: control model below 7/10")
    if chaos > 6.5:
        no_bets.append("High chaos score: reduce stake or no bet")
    if home_tdi >= 2 and away_tdi >= 2:
        no_bets.append("Kellerduell / both teams TDI >= 2: Over 1.5 locked")
        locks.append("over_1_5_cellar_duel_lock")

    # Away favorite degradation rule.
    formation_home_xg90 = _n(row, "formation_home_xg90", np.nan)
    away_market_fav = False
    if pd.notna(_n(row, "odds_away", np.nan)) and pd.notna(_n(row, "odds_home", np.nan)):
        away_market_fav = _n(row, "odds_away") < _n(row, "odds_home")
    away_model_fav = top_label == "A"
    if (away_market_fav or away_model_fav) and pd.notna(formation_home_xg90) and formation_home_xg90 >= 1.20:
        no_bets.append("Away-favorite degradation: home formation xG90 >= 1.20")
        locks.append("away_favorite_degradation")

    if control >= 7.0 and prob_edge >= 0.06 and top_prob >= 0.42 and chaos <= 6.5 and top_label != "D":
        value = _market_value(row, top_label, top_prob)
        recommendations.append({
            "market": "1X2",
            "selection": LABELS[top_label],
            "confidence": round(control / 10.0, 2),
            "probability": round(top_prob, 4),
            "value": value,
            "reason": "Top probability clears control, edge and chaos thresholds",
        })

    # DNB 5+1 conditions.
    side_label = "H" if probs.get("H", 0) >= probs.get("A", 0) else "A"
    side = "home" if side_label == "H" else "away"
    opp = "away" if side == "home" else "home"
    xg_edge = _n(row, "edge_w5_xgdiff", 0.0)
    if side_label == "A":
        xg_edge = -xg_edge
    side_tdi = home_tdi if side == "home" else away_tdi
    opp_tdi = away_tdi if side == "home" else home_tdi
    dnb_conditions = {
        "prob_edge_vs_opponent": probs[side_label] - probs["A" if side_label == "H" else "H"] >= 0.07,
        "xg_edge_positive": xg_edge >= 0.10,
        "side_tdi_ok": side_tdi <= 1 or side_tdi <= opp_tdi,
        "chaos_ok": chaos <= 5.8,
        "control_ok": control >= 6.5,
        "not_away_degradation": "away_favorite_degradation" not in locks,
    }
    if all(dnb_conditions.values()):
        recommendations.append({
            "market": "DNB",
            "selection": LABELS[side_label],
            "confidence": round(min(0.92, control / 10.0 + 0.04), 2),
            "probability": round(probs[side_label], 4),
            "conditions": dnb_conditions,
            "reason": "All 5+1 DNB conditions passed",
        })
    else:
        no_bets.append("DNB locked: " + ", ".join([k for k, v in dnb_conditions.items() if not v]))

    # Conservative totals signal, not a trained totals model.
    if pd.notna(expected_total):
        if expected_total >= 2.65 and "over_1_5_cellar_duel_lock" not in locks and chaos <= 6.5:
            recommendations.append({
                "market": "Over 1.5 goals",
                "selection": "Over 1.5",
                "confidence": round(min(0.85, 0.50 + (expected_total - 2.0) / 3.0), 2),
                "model_total_xg_proxy": round(float(expected_total), 3),
                "reason": "Rolling xG total is supportive and no cellar-duel lock fired",
            })
        elif "over_1_5_cellar_duel_lock" not in locks:
            no_bets.append("Over 1.5 not recommended: xG total proxy below threshold")

    if not recommendations:
        no_bets.append("No primary betting recommendation cleared all v1.9 gates")

    return {
        "probabilities": {
            "home": round(probs.get("H", 0.0), 4),
            "draw": round(probs.get("D", 0.0), 4),
            "away": round(probs.get("A", 0.0), 4),
        },
        "top_model_side": LABELS[top_label],
        "control_model_score": control,
        "chaos_score": chaos,
        "tdi": {"home": home_tdi, "away": away_tdi},
        "score_family": score_family(row, probs),
        "locks": locks,
        "recommendations": recommendations,
        "no_bets": list(dict.fromkeys(no_bets)),
    }
