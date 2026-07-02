# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v2104_indicator_shadow_common import (
    build_shadow_result_dict,
    load_match_rows,
    preserve_home_away_ratio_adjust_draw,
    prior_rows,
    quality_from_match_counts,
    team_matches,
)


def build_draw_tendency_indicator(
    competition: str,
    season: str,
    home_team: str,
    away_team: str,
    match_date: str,
    base_home_probability: float = 0.34,
    base_draw_probability: float = 0.32,
    base_away_probability: float = 0.34,
    draw_baseline_rate: float = 0.27,
    source_profile: str | None = None,
    cache_only: bool = True,
    enable_network: bool = False,
) -> dict[str, object]:
    del source_profile
    if not competition or not season or not home_team or not away_team or not match_date:
        return _empty(base_home_probability, base_draw_probability, base_away_probability, "competition, season, teams and match_date are required")
    matches = prior_rows(_load_match_rows(competition, season, home_team, away_team, match_date, cache_only=cache_only, enable_network=enable_network), match_date)
    home = team_matches(matches, home_team)
    away = team_matches(matches, away_team)
    home_draws = int(_draw_mask(home).sum()) if not home.empty else 0
    away_draws = int(_draw_mask(away).sum()) if not away.empty else 0
    home_n = int(len(home))
    away_n = int(len(away))
    quality = quality_from_match_counts(home_n, away_n)
    home_rate = round(home_draws / home_n, 4) if home_n else 0.0
    away_rate = round(away_draws / away_n, 4) if away_n else 0.0
    combined = round((home_draws + away_draws) / (home_n + away_n), 4) if home_n + away_n else 0.0
    diff = round(combined - draw_baseline_rate, 4)
    strength = min(0.04, max(0.0, abs(diff) * 0.5)) if quality != "LOW" and abs(diff) >= 0.04 else 0.0
    adjusted = preserve_home_away_ratio_adjust_draw(base_home_probability, base_draw_probability, base_away_probability, strength if diff > 0 else -strength) if strength else None
    reason = "LOW quality draw tendency; no adjustment" if quality == "LOW" else ("Draw tendency near baseline; no adjustment" if not strength else "Combined draw tendency shifted diagnostic draw probability")
    result = build_shadow_result_dict("dt", "DRAW_TENDENCY", quality, reason, base_home_probability, base_draw_probability, base_away_probability, adjusted, strength, bool(strength), reason)
    result.update(
        {
            "dt_home_draws_before_match": home_draws,
            "dt_away_draws_before_match": away_draws,
            "dt_home_draw_rate_before_match": home_rate,
            "dt_away_draw_rate_before_match": away_rate,
            "dt_combined_draw_rate_before_match": combined,
            "dt_draw_baseline_rate": round(draw_baseline_rate, 4),
            "dt_draw_tendency_diff": diff,
        }
    )
    return result


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    return load_match_rows(competition, season, home_team, away_team, match_date, "v2104_draw_tendency", cache_only=cache_only, enable_network=enable_network)


def _draw_mask(frame: pd.DataFrame) -> pd.Series:
    return frame["home_goals"].astype(float).eq(frame["away_goals"].astype(float))


def _empty(base_home: float, base_draw: float, base_away: float, reason: str) -> dict[str, object]:
    result = build_shadow_result_dict("dt", "DRAW_TENDENCY", "LOW", reason, base_home, base_draw, base_away, None, 0.0, False, reason)
    result.update(
        {
            "dt_home_draws_before_match": 0,
            "dt_away_draws_before_match": 0,
            "dt_home_draw_rate_before_match": 0.0,
            "dt_away_draw_rate_before_match": 0.0,
            "dt_combined_draw_rate_before_match": 0.0,
            "dt_draw_baseline_rate": 0.27,
            "dt_draw_tendency_diff": 0.0,
        }
    )
    return result
