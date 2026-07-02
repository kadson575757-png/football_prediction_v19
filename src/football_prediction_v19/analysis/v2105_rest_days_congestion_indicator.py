# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date

import pandas as pd

from football_prediction_v19.analysis.v20_historical_match_context import normalize_match_date
from football_prediction_v19.analysis.v2104_indicator_shadow_common import apply_home_away_shift, build_shadow_result_dict, load_match_rows, prior_rows, quality_from_match_counts, team_matches


def build_rest_days_congestion_indicator(
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
    target = date.fromisoformat(normalize_match_date(match_date))
    matches = prior_rows(_load_match_rows(competition, season, home_team, away_team, match_date, cache_only=cache_only, enable_network=enable_network), match_date)
    home_rows = team_matches(matches, home_team)
    away_rows = team_matches(matches, away_team)
    home_n = len(home_rows)
    away_n = len(away_rows)
    quality = quality_from_match_counts(home_n, away_n)
    home_days = _days_since_last(home_rows, target)
    away_days = _days_since_last(away_rows, target)
    home_14 = _matches_last_days(home_rows, target, 14)
    away_14 = _matches_last_days(away_rows, target, 14)
    rest_diff = int(home_days - away_days) if home_days >= 0 and away_days >= 0 else 0
    congestion_diff = int(away_14 - home_14)
    signal = round(rest_diff + congestion_diff * 1.5, 4)
    strength = min(0.035, abs(signal) * 0.004) if quality != "LOW" and abs(signal) >= 3 else 0.0
    adjusted = apply_home_away_shift(base_home_probability, base_draw_probability, base_away_probability, strength if signal > 0 else -strength) if strength else None
    reason = "LOW quality rest/congestion profile; no adjustment" if quality == "LOW" else ("Rest and congestion profile near neutral; no adjustment" if not strength else "Rest and congestion profile shifted diagnostic probability")
    result = build_shadow_result_dict("rdc", "REST_DAYS_CONGESTION_PROFILE", quality, reason, base_home_probability, base_draw_probability, base_away_probability, adjusted, strength, bool(strength), reason)
    result.update(
        {
            "rdc_home_days_since_last_match": home_days,
            "rdc_away_days_since_last_match": away_days,
            "rdc_rest_days_diff": rest_diff,
            "rdc_home_matches_last_14_days": home_14,
            "rdc_away_matches_last_14_days": away_14,
            "rdc_congestion_diff": congestion_diff,
            "rdc_rest_advantage_signal": signal,
        }
    )
    return result


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    return load_match_rows(competition, season, home_team, away_team, match_date, "v2105_rest_days_congestion", cache_only=cache_only, enable_network=enable_network)


def _days_since_last(frame: pd.DataFrame, target: date) -> int:
    dates = [date.fromisoformat(normalize_match_date(str(value))) for value in frame.get("match_date", [])]
    return min((target - max(dates)).days, 999) if dates else -1


def _matches_last_days(frame: pd.DataFrame, target: date, days: int) -> int:
    dates = [date.fromisoformat(normalize_match_date(str(value))) for value in frame.get("match_date", [])]
    return sum(1 for value in dates if 0 < (target - value).days <= days)


def _empty(base_home: float, base_draw: float, base_away: float, reason: str) -> dict[str, object]:
    result = build_shadow_result_dict("rdc", "REST_DAYS_CONGESTION_PROFILE", "LOW", reason, base_home, base_draw, base_away, None, 0.0, False, reason)
    result.update({"rdc_home_days_since_last_match": -1, "rdc_away_days_since_last_match": -1, "rdc_rest_days_diff": 0, "rdc_home_matches_last_14_days": 0, "rdc_away_matches_last_14_days": 0, "rdc_congestion_diff": 0, "rdc_rest_advantage_signal": 0.0})
    return result
