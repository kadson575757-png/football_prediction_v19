# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league
from football_prediction_v19.analysis.v2104_indicator_shadow_common import apply_home_away_shift, build_shadow_result_dict, load_match_rows, preserve_home_away_ratio_adjust_draw, prior_rows, quality_from_match_counts, team_matches


def build_result_streak_indicator(
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
    quality = quality_from_match_counts(len(home_rows), len(away_rows))
    home = _streaks(home_rows, home_team)
    away = _streaks(away_rows, away_team)
    streak_signal = round((home["win"] + home["unbeaten"] * 0.5 + away["loss"] + away["winless"] * 0.5) - (away["win"] + away["unbeaten"] * 0.5 + home["loss"] + home["winless"] * 0.5), 4)
    draw_signal = round(min(home["draw"], away["draw"]) + min(home["winless"], away["winless"]) * 0.5, 4)
    strength = 0.0
    adjusted = None
    if quality != "LOW" and draw_signal >= 2 and abs(streak_signal) <= 2:
        strength = min(0.025, draw_signal * 0.006)
        adjusted = preserve_home_away_ratio_adjust_draw(base_home_probability, base_draw_probability, base_away_probability, strength)
    elif quality != "LOW" and abs(streak_signal) >= 2:
        strength = min(0.04, abs(streak_signal) * 0.006)
        adjusted = apply_home_away_shift(base_home_probability, base_draw_probability, base_away_probability, strength if streak_signal > 0 else -strength)
    reason = "LOW quality result streak profile; no adjustment" if quality == "LOW" else ("Result streak profile near neutral; no adjustment" if not adjusted else "Result streak profile shifted diagnostic probability")
    result = build_shadow_result_dict("rsp", "RESULT_STREAK_PROFILE", quality, reason, base_home_probability, base_draw_probability, base_away_probability, adjusted, strength, bool(strength), reason)
    result.update({
        "rsp_home_win_streak": home["win"], "rsp_home_unbeaten_streak": home["unbeaten"], "rsp_home_loss_streak": home["loss"], "rsp_home_winless_streak": home["winless"],
        "rsp_away_win_streak": away["win"], "rsp_away_unbeaten_streak": away["unbeaten"], "rsp_away_loss_streak": away["loss"], "rsp_away_winless_streak": away["winless"],
        "rsp_streak_signal": streak_signal, "rsp_draw_streak_signal": draw_signal,
    })
    return result


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    return load_match_rows(competition, season, home_team, away_team, match_date, "v2107_result_streak", cache_only=cache_only, enable_network=enable_network)


def _streaks(frame: pd.DataFrame, team: str) -> dict[str, int]:
    results = [_result(row, team) for _, row in frame.iterrows()]
    return {
        "win": _tail_count(results, {"W"}),
        "unbeaten": _tail_count(results, {"W", "D"}),
        "loss": _tail_count(results, {"L"}),
        "winless": _tail_count(results, {"L", "D"}),
        "draw": _tail_count(results, {"D"}),
    }


def _result(row: pd.Series, team: str) -> str:
    team_norm = normalize_team_or_league(team)
    is_home = normalize_team_or_league(row.get("home_team", "")) == team_norm
    gf = float(row.get("home_goals" if is_home else "away_goals", 0))
    ga = float(row.get("away_goals" if is_home else "home_goals", 0))
    return "W" if gf > ga else ("D" if gf == ga else "L")


def _tail_count(values: list[str], allowed: set[str]) -> int:
    count = 0
    for value in reversed(values):
        if value not in allowed:
            break
        count += 1
    return count


def _empty(base_home: float, base_draw: float, base_away: float, reason: str) -> dict[str, object]:
    result = build_shadow_result_dict("rsp", "RESULT_STREAK_PROFILE", "LOW", reason, base_home, base_draw, base_away, None, 0.0, False, reason)
    result.update({"rsp_home_win_streak": 0, "rsp_home_unbeaten_streak": 0, "rsp_home_loss_streak": 0, "rsp_home_winless_streak": 0, "rsp_away_win_streak": 0, "rsp_away_unbeaten_streak": 0, "rsp_away_loss_streak": 0, "rsp_away_winless_streak": 0, "rsp_streak_signal": 0.0, "rsp_draw_streak_signal": 0.0})
    return result
