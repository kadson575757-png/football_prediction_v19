# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league
from football_prediction_v19.analysis.v2104_indicator_shadow_common import apply_home_away_shift, build_shadow_result_dict, load_match_rows, preserve_home_away_ratio_adjust_draw, prior_rows, team_matches


def build_response_after_result_indicator(
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
    home_rows = team_matches(matches, home_team).sort_values("match_date")
    away_rows = team_matches(matches, away_team).sort_values("match_date")
    home_prev = _last_result(home_rows, home_team)
    away_prev = _last_result(away_rows, away_team)
    home = _points_after_result(home_rows, home_team, home_prev)
    away = _points_after_result(away_rows, away_team, away_prev)
    quality = "FULL" if home["matches"] >= 8 and away["matches"] >= 8 else ("PARTIAL" if home["matches"] >= 3 and away["matches"] >= 3 else "LOW")
    home_ppg = round(home["points"] / home["matches"], 4) if home["matches"] else 0.0
    away_ppg = round(away["points"] / away["matches"], 4) if away["matches"] else 0.0
    home_signal = round(home_ppg - 1.0, 4)
    away_signal = round(away_ppg - 1.0, 4)
    signal = round(home_signal - away_signal, 4)
    strength = 0.0
    adjusted = None
    if quality != "LOW" and home_prev == away_prev == "D":
        strength = 0.01
        adjusted = preserve_home_away_ratio_adjust_draw(base_home_probability, base_draw_probability, base_away_probability, strength)
    elif quality != "LOW" and abs(signal) >= 0.2:
        strength = min(0.035, abs(signal) * 0.025)
        adjusted = apply_home_away_shift(base_home_probability, base_draw_probability, base_away_probability, strength if signal > 0 else -strength)
    reason = "LOW quality response-after-result profile; no adjustment" if quality == "LOW" else ("Response-after-result profile shifted diagnostic probability" if adjusted else "Response-after-result profile near neutral; no adjustment")
    result = build_shadow_result_dict("rar", "RESPONSE_AFTER_RESULT_PROFILE", quality, reason, base_home_probability, base_draw_probability, base_away_probability, adjusted, strength, bool(strength), reason)
    result.update({"rar_home_previous_result": home_prev, "rar_away_previous_result": away_prev, "rar_home_points_after_previous_result_type": int(home["points"]), "rar_away_points_after_previous_result_type": int(away["points"]), "rar_home_ppg_after_previous_result_type": home_ppg, "rar_away_ppg_after_previous_result_type": away_ppg, "rar_home_bounce_back_signal": home_signal, "rar_away_bounce_back_signal": away_signal, "rar_response_signal": signal})
    return result


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    return load_match_rows(competition, season, home_team, away_team, match_date, "v2108_response_after_result", cache_only=cache_only, enable_network=enable_network)


def _last_result(frame: pd.DataFrame, team: str) -> str:
    if frame.empty:
        return "UNKNOWN"
    return _result(frame.iloc[-1], team)


def _points_after_result(frame: pd.DataFrame, team: str, result_type: str) -> dict[str, int]:
    out = {"points": 0, "matches": 0}
    if result_type == "UNKNOWN":
        return out
    rows = list(frame.iterrows())
    for idx in range(len(rows) - 1):
        if _result(rows[idx][1], team) != result_type:
            continue
        out["points"] += _points(rows[idx + 1][1], team)
        out["matches"] += 1
    return out


def _result(row: pd.Series, team: str) -> str:
    pts = _points(row, team)
    return "W" if pts == 3 else ("D" if pts == 1 else "L")


def _points(row: pd.Series, team: str) -> int:
    team_norm = normalize_team_or_league(team)
    is_home = normalize_team_or_league(row.get("home_team", "")) == team_norm
    gf = float(row.get("home_goals" if is_home else "away_goals", 0))
    ga = float(row.get("away_goals" if is_home else "home_goals", 0))
    return 3 if gf > ga else (1 if gf == ga else 0)


def _empty(base_home: float, base_draw: float, base_away: float, reason: str) -> dict[str, object]:
    result = build_shadow_result_dict("rar", "RESPONSE_AFTER_RESULT_PROFILE", "LOW", reason, base_home, base_draw, base_away, None, 0.0, False, reason)
    result.update({"rar_home_previous_result": "UNKNOWN", "rar_away_previous_result": "UNKNOWN", "rar_home_points_after_previous_result_type": 0, "rar_away_points_after_previous_result_type": 0, "rar_home_ppg_after_previous_result_type": 0.0, "rar_away_ppg_after_previous_result_type": 0.0, "rar_home_bounce_back_signal": 0.0, "rar_away_bounce_back_signal": 0.0, "rar_response_signal": 0.0})
    return result
