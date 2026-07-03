# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any

from football_prediction_v19.analysis.v2104_indicator_shadow_common import apply_home_away_shift, build_shadow_result_dict, normalize_probabilities, preserve_home_away_ratio_adjust_draw


PRIOR_PREFIXES = ["dt", "vr", "gm", "vsb", "csfts", "rdc", "tsg", "cbl", "oarf", "rgt", "vrm", "rvc", "rsp", "srp", "h2hc", "lzp", "cop", "sbp", "rar", "hre"]


def build_shadow_consensus_alignment_indicator(
    base_home_probability: float,
    base_draw_probability: float,
    base_away_probability: float,
    shadow_source: dict[str, Any] | None = None,
) -> dict[str, object]:
    base_home, base_draw, base_away = normalize_probabilities(base_home_probability, base_draw_probability, base_away_probability)
    base_top = _top(base_home, base_draw, base_away)
    support = {"HOME": 0.0, "DRAW": 0.0, "AWAY": 0.0}
    available = 0
    for prefix in PRIOR_PREFIXES:
        source = shadow_source or {}
        quality = str(source.get(f"{prefix}_indicator_quality", "FULL"))
        if quality == "LOW":
            continue
        if f"{prefix}_adjusted_home_win_probability" not in source:
            continue
        home = _num(source.get(f"{prefix}_adjusted_home_win_probability"))
        draw = _num(source.get(f"{prefix}_adjusted_draw_probability"))
        away = _num(source.get(f"{prefix}_adjusted_away_probability"))
        outcome = _top(home, draw, away)
        weight = 1.0 if _truthy(source.get(f"{prefix}_adjustment_applied", True)) else 0.5
        support[outcome] += weight
        available += 1
    quality = "FULL" if available >= 8 else ("PARTIAL" if available >= 3 else "LOW")
    consensus = max(support.items(), key=lambda item: item[1])[0]
    consensus_support = support[consensus]
    conflict = round(sum(value for outcome, value in support.items() if outcome != base_top), 4)
    strength_score = round(consensus_support / max(1.0, sum(support.values())), 4)
    alignment = round(strength_score if consensus == base_top else -strength_score, 4)
    adjusted = None
    strength = 0.0
    if quality != "LOW" and consensus == "DRAW" and consensus != base_top:
        strength = min(0.035, strength_score * 0.04)
        adjusted = preserve_home_away_ratio_adjust_draw(base_home, base_draw, base_away, strength)
    elif quality != "LOW" and consensus != base_top and consensus_support >= 2:
        strength = min(0.035, strength_score * 0.04)
        adjusted = apply_home_away_shift(base_home, base_draw, base_away, strength if consensus == "HOME" else -strength)
    elif quality != "LOW" and consensus == base_top and consensus_support >= 2:
        strength = min(0.025, strength_score * 0.03)
        if base_top == "DRAW":
            adjusted = preserve_home_away_ratio_adjust_draw(base_home, base_draw, base_away, strength)
        else:
            adjusted = apply_home_away_shift(base_home, base_draw, base_away, strength if base_top == "HOME" else -strength)
    reason = "LOW quality shadow consensus; no adjustment" if quality == "LOW" else ("Shadow consensus alignment shifted diagnostic probability" if adjusted else "Shadow consensus alignment near neutral; no adjustment")
    result = build_shadow_result_dict("sca", "SHADOW_CONSENSUS_ALIGNMENT_PROFILE", quality, reason, base_home, base_draw, base_away, adjusted, strength, bool(strength), reason)
    result.update({"sca_available_shadow_count": available, "sca_home_support_count": round(support["HOME"], 4), "sca_draw_support_count": round(support["DRAW"], 4), "sca_away_support_count": round(support["AWAY"], 4), "sca_base_top_outcome": base_top, "sca_consensus_top_outcome": consensus, "sca_consensus_support_count": round(consensus_support, 4), "sca_conflict_count": conflict, "sca_consensus_strength": strength_score, "sca_alignment_signal": alignment})
    return result


def _top(home: float, draw: float, away: float) -> str:
    return max({"HOME": home, "DRAW": draw, "AWAY": away}.items(), key=lambda item: item[1])[0]


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _num(value: object) -> float:
    try:
        if str(value).strip() == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
