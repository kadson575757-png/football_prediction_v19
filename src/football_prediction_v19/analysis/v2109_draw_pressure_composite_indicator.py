# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v2104_indicator_shadow_common import build_shadow_result_dict, load_match_rows, preserve_home_away_ratio_adjust_draw, prior_rows, quality_from_match_counts, team_matches


def build_draw_pressure_composite_indicator(
    competition: str,
    season: str,
    home_team: str,
    away_team: str,
    match_date: str,
    base_home_probability: float = 0.34,
    base_draw_probability: float = 0.32,
    base_away_probability: float = 0.34,
    source_profile: str | None = None,
    cache_only: bool = True,
    enable_network: bool = False,
) -> dict[str, object]:
    del source_profile
    if not competition or not season or not home_team or not away_team or not match_date:
        return _empty(base_home_probability, base_draw_probability, base_away_probability, "competition, season, teams and match_date are required")
    matches = prior_rows(_load_match_rows(competition, season, home_team, away_team, match_date, cache_only=cache_only, enable_network=enable_network), match_date)
    home_rows = team_matches(matches, home_team)
    away_rows = team_matches(matches, away_team)
    quality = quality_from_match_counts(len(home_rows), len(away_rows))
    home = _profile(home_rows, home_team)
    away = _profile(away_rows, away_team)
    combined_draw = round((home["draw_rate"] + away["draw_rate"]) / 2, 4)
    combined_narrow = round((home["narrow_rate"] + away["narrow_rate"]) / 2, 4)
    similarity = round(max(0.0, 1.0 - abs(home["ppg"] - away["ppg"]) / 3.0 - abs(home["gdpm"] - away["gdpm"]) / 4.0), 4)
    edge = _base_edge(base_home_probability, base_draw_probability, base_away_probability)
    signal = round(combined_draw * 0.35 + combined_narrow * 0.25 + ((home["low_margin_rate"] + away["low_margin_rate"]) / 2) * 0.2 + similarity * 0.2 - edge * 0.25, 4)
    strength = min(0.035, max(0.0, signal - 0.35) * 0.05) if quality != "LOW" else 0.0
    adjusted = preserve_home_away_ratio_adjust_draw(base_home_probability, base_draw_probability, base_away_probability, strength) if strength else None
    reason = "LOW quality draw pressure composite; no adjustment" if quality == "LOW" else ("Draw pressure composite shifted diagnostic probability" if adjusted else "Draw pressure composite near neutral; no adjustment")
    result = build_shadow_result_dict("dpc", "DRAW_PRESSURE_COMPOSITE_PROFILE", quality, reason, base_home_probability, base_draw_probability, base_away_probability, adjusted, strength, bool(strength), reason)
    result.update({"dpc_home_draw_rate": home["draw_rate"], "dpc_away_draw_rate": away["draw_rate"], "dpc_combined_draw_rate": combined_draw, "dpc_home_narrow_match_rate": home["narrow_rate"], "dpc_away_narrow_match_rate": away["narrow_rate"], "dpc_combined_narrow_match_rate": combined_narrow, "dpc_home_low_margin_rate": home["low_margin_rate"], "dpc_away_low_margin_rate": away["low_margin_rate"], "dpc_strength_similarity_score": similarity, "dpc_base_probability_edge": edge, "dpc_draw_pressure_signal": signal})
    return result


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    return load_match_rows(competition, season, home_team, away_team, match_date, "v2109_draw_pressure_composite", cache_only=cache_only, enable_network=enable_network)


def _profile(frame: pd.DataFrame, team: str) -> dict[str, float]:
    if frame.empty:
        return {"draw_rate": 0.0, "narrow_rate": 0.0, "low_margin_rate": 0.0, "ppg": 0.0, "gdpm": 0.0}
    draws = narrow = low = points = 0
    gd = 0.0
    for _, row in frame.iterrows():
        is_home = str(row.get("home_team", "")).casefold() == str(team).casefold()
        gf = float(row.get("home_goals" if is_home else "away_goals", 0))
        ga = float(row.get("away_goals" if is_home else "home_goals", 0))
        margin = gf - ga
        gd += margin
        draws += int(margin == 0)
        narrow += int(abs(margin) <= 1)
        low += int(margin == 0 or abs(margin) == 1)
        points += 3 if margin > 0 else (1 if margin == 0 else 0)
    n = len(frame)
    return {"draw_rate": round(draws / n, 4), "narrow_rate": round(narrow / n, 4), "low_margin_rate": round(low / n, 4), "ppg": round(points / n, 4), "gdpm": round(gd / n, 4)}


def _base_edge(home: float, draw: float, away: float) -> float:
    values = sorted([float(home), float(draw), float(away)], reverse=True)
    return round(values[0] - values[1], 4)


def _empty(base_home: float, base_draw: float, base_away: float, reason: str) -> dict[str, object]:
    result = build_shadow_result_dict("dpc", "DRAW_PRESSURE_COMPOSITE_PROFILE", "LOW", reason, base_home, base_draw, base_away, None, 0.0, False, reason)
    result.update({"dpc_home_draw_rate": 0.0, "dpc_away_draw_rate": 0.0, "dpc_combined_draw_rate": 0.0, "dpc_home_narrow_match_rate": 0.0, "dpc_away_narrow_match_rate": 0.0, "dpc_combined_narrow_match_rate": 0.0, "dpc_home_low_margin_rate": 0.0, "dpc_away_low_margin_rate": 0.0, "dpc_strength_similarity_score": 0.0, "dpc_base_probability_edge": 0.0, "dpc_draw_pressure_signal": 0.0})
    return result
