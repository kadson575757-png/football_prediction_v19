# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league
from football_prediction_v19.analysis.v2104_indicator_shadow_common import apply_home_away_shift, build_shadow_result_dict, load_match_rows, preserve_home_away_ratio_adjust_draw, prior_rows, quality_from_match_counts, team_matches


def build_league_zone_pressure_indicator(
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
    home_n = len(team_matches(matches, home_team))
    away_n = len(team_matches(matches, away_team))
    quality = quality_from_match_counts(home_n, away_n)
    table = _table(matches)
    teams_count = len(table)
    home = table.get(normalize_team_or_league(home_team), {"points": 0, "matches": 0, "rank": 0})
    away = table.get(normalize_team_or_league(away_team), {"points": 0, "matches": 0, "rank": 0})
    home_zone = _zone(int(home["rank"]), teams_count)
    away_zone = _zone(int(away["rank"]), teams_count)
    rank_gap = int(away["rank"] - home["rank"]) if home["rank"] and away["rank"] else 0
    points_gap = int(home["points"] - away["points"])
    avg_matches = ((home["matches"] or 0) + (away["matches"] or 0)) / 2
    phase = "early" if avg_matches < 10 else ("mid" if avg_matches <= 24 else "late")
    zone_diff = _zone_score(home_zone) - _zone_score(away_zone)
    signal = round(zone_diff * 0.55 + rank_gap * 0.08 + points_gap * 0.03, 4)
    if phase == "late":
        signal = round(signal * 1.15, 4)
    strength = 0.0
    adjusted = None
    if quality != "LOW" and home_zone == away_zone and abs(rank_gap) <= 2 and abs(points_gap) <= 4:
        strength = 0.012
        adjusted = preserve_home_away_ratio_adjust_draw(base_home_probability, base_draw_probability, base_away_probability, strength)
    elif quality != "LOW" and abs(signal) >= 0.45:
        strength = min(0.04, abs(signal) * 0.018)
        adjusted = apply_home_away_shift(base_home_probability, base_draw_probability, base_away_probability, strength if signal > 0 else -strength)
    reason = "LOW quality league zone pressure profile; no adjustment" if quality == "LOW" else ("League zone pressure profile near neutral; no adjustment" if not adjusted else "League zone pressure profile shifted diagnostic probability")
    result = build_shadow_result_dict("lzp", "LEAGUE_ZONE_PRESSURE_PROFILE", quality, reason, base_home_probability, base_draw_probability, base_away_probability, adjusted, strength, bool(strength), reason)
    result.update({"lzp_home_rank_before_match": int(home["rank"]), "lzp_away_rank_before_match": int(away["rank"]), "lzp_home_points_before_match": int(home["points"]), "lzp_away_points_before_match": int(away["points"]), "lzp_home_matches_before_match": int(home["matches"]), "lzp_away_matches_before_match": int(away["matches"]), "lzp_home_zone": home_zone, "lzp_away_zone": away_zone, "lzp_rank_gap": rank_gap, "lzp_points_gap": points_gap, "lzp_season_phase": phase, "lzp_pressure_signal": signal})
    return result


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    return load_match_rows(competition, season, home_team, away_team, match_date, "v2107_league_zone_pressure", cache_only=cache_only, enable_network=enable_network)


def _table(frame: pd.DataFrame) -> dict[str, dict[str, int]]:
    table: dict[str, dict[str, int]] = {}
    for _, row in frame.iterrows():
        home = normalize_team_or_league(row.get("home_team", ""))
        away = normalize_team_or_league(row.get("away_team", ""))
        table.setdefault(home, {"points": 0, "matches": 0, "rank": 0, "gd": 0})
        table.setdefault(away, {"points": 0, "matches": 0, "rank": 0, "gd": 0})
        hg = int(float(row.get("home_goals", 0)))
        ag = int(float(row.get("away_goals", 0)))
        table[home]["matches"] += 1
        table[away]["matches"] += 1
        table[home]["gd"] += hg - ag
        table[away]["gd"] += ag - hg
        if hg > ag:
            table[home]["points"] += 3
        elif ag > hg:
            table[away]["points"] += 3
        else:
            table[home]["points"] += 1
            table[away]["points"] += 1
    ranked = sorted(table.items(), key=lambda item: (item[1]["points"], item[1]["gd"]), reverse=True)
    for index, (_, values) in enumerate(ranked, start=1):
        values["rank"] = index
    return table


def _zone(rank: int, teams_count: int) -> str:
    if not rank or not teams_count:
        return "unknown"
    if rank <= 3:
        return "title_zone"
    if rank <= 7:
        return "top_zone"
    if rank > max(0, teams_count - 3):
        return "relegation_zone"
    return "mid_table"


def _zone_score(zone: str) -> int:
    return {"title_zone": 3, "top_zone": 2, "mid_table": 1, "relegation_zone": 0}.get(zone, 0)


def _empty(base_home: float, base_draw: float, base_away: float, reason: str) -> dict[str, object]:
    result = build_shadow_result_dict("lzp", "LEAGUE_ZONE_PRESSURE_PROFILE", "LOW", reason, base_home, base_draw, base_away, None, 0.0, False, reason)
    result.update({"lzp_home_rank_before_match": 0, "lzp_away_rank_before_match": 0, "lzp_home_points_before_match": 0, "lzp_away_points_before_match": 0, "lzp_home_matches_before_match": 0, "lzp_away_matches_before_match": 0, "lzp_home_zone": "unknown", "lzp_away_zone": "unknown", "lzp_rank_gap": 0, "lzp_points_gap": 0, "lzp_season_phase": "early", "lzp_pressure_signal": 0.0})
    return result
