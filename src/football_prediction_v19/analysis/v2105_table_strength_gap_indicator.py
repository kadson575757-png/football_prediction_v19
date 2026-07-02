# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league
from football_prediction_v19.analysis.v2104_indicator_shadow_common import apply_home_away_shift, build_shadow_result_dict, load_match_rows, preserve_home_away_ratio_adjust_draw, prior_rows, quality_from_match_counts, team_matches


def build_table_strength_gap_indicator(
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
    home = table.get(normalize_team_or_league(home_team), {"points": 0, "matches": 0, "rank": 0})
    away = table.get(normalize_team_or_league(away_team), {"points": 0, "matches": 0, "rank": 0})
    home_ppg = round(home["points"] / home["matches"], 4) if home["matches"] else 0.0
    away_ppg = round(away["points"] / away["matches"], 4) if away["matches"] else 0.0
    ppg_diff = round(home_ppg - away_ppg, 4)
    rank_gap = int(away["rank"] - home["rank"]) if home["rank"] and away["rank"] else 0
    signal = round(ppg_diff + rank_gap * 0.03, 4)
    strength = 0.0
    adjusted = None
    if quality != "LOW" and abs(ppg_diff) < 0.15 and abs(rank_gap) <= 2:
        strength = 0.012
        adjusted = preserve_home_away_ratio_adjust_draw(base_home_probability, base_draw_probability, base_away_probability, strength)
    elif quality != "LOW" and abs(signal) >= 0.25:
        strength = min(0.04, abs(signal) * 0.025)
        adjusted = apply_home_away_shift(base_home_probability, base_draw_probability, base_away_probability, strength if signal > 0 else -strength)
    reason = "LOW quality table strength gap; no adjustment" if quality == "LOW" else ("Table strength gap near neutral; draw shadow increased slightly" if adjusted and abs(signal) < 0.25 else ("Table strength gap near neutral; no adjustment" if not adjusted else "Table strength gap shifted diagnostic probability"))
    result = build_shadow_result_dict("tsg", "TABLE_STRENGTH_GAP_PROFILE", quality, reason, base_home_probability, base_draw_probability, base_away_probability, adjusted, strength, bool(strength), reason)
    result.update(
        {
            "tsg_home_points_before_match": int(home["points"]),
            "tsg_away_points_before_match": int(away["points"]),
            "tsg_home_points_per_match": home_ppg,
            "tsg_away_points_per_match": away_ppg,
            "tsg_points_per_match_diff": ppg_diff,
            "tsg_home_rank_before_match": int(home["rank"]),
            "tsg_away_rank_before_match": int(away["rank"]),
            "tsg_rank_gap": rank_gap,
            "tsg_strength_signal": signal,
        }
    )
    return result


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    return load_match_rows(competition, season, home_team, away_team, match_date, "v2105_table_strength_gap", cache_only=cache_only, enable_network=enable_network)


def _table(frame: pd.DataFrame) -> dict[str, dict[str, int]]:
    table: dict[str, dict[str, int]] = {}
    for _, row in frame.iterrows():
        home = normalize_team_or_league(row.get("home_team", ""))
        away = normalize_team_or_league(row.get("away_team", ""))
        table.setdefault(home, {"points": 0, "matches": 0, "rank": 0})
        table.setdefault(away, {"points": 0, "matches": 0, "rank": 0})
        hg = float(row.get("home_goals", 0))
        ag = float(row.get("away_goals", 0))
        table[home]["matches"] += 1
        table[away]["matches"] += 1
        if hg > ag:
            table[home]["points"] += 3
        elif ag > hg:
            table[away]["points"] += 3
        else:
            table[home]["points"] += 1
            table[away]["points"] += 1
    ranked = sorted(table.items(), key=lambda item: (item[1]["points"] / item[1]["matches"] if item[1]["matches"] else 0, item[1]["points"]), reverse=True)
    for index, (_, values) in enumerate(ranked, start=1):
        values["rank"] = index
    return table


def _empty(base_home: float, base_draw: float, base_away: float, reason: str) -> dict[str, object]:
    result = build_shadow_result_dict("tsg", "TABLE_STRENGTH_GAP_PROFILE", "LOW", reason, base_home, base_draw, base_away, None, 0.0, False, reason)
    result.update({"tsg_home_points_before_match": 0, "tsg_away_points_before_match": 0, "tsg_home_points_per_match": 0.0, "tsg_away_points_per_match": 0.0, "tsg_points_per_match_diff": 0.0, "tsg_home_rank_before_match": 0, "tsg_away_rank_before_match": 0, "tsg_rank_gap": 0, "tsg_strength_signal": 0.0})
    return result
