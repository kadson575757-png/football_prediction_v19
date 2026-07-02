# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v2104_indicator_shadow_common import (
    apply_home_away_shift,
    build_shadow_result_dict,
    load_match_rows,
    preserve_home_away_ratio_adjust_draw,
    prior_rows,
    quality_from_match_counts,
    venue_matches,
)


def build_venue_result_rate_indicator(
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
    home_rows = venue_matches(matches, home_team, "home")
    away_rows = venue_matches(matches, away_team, "away")
    home_n = int(len(home_rows))
    away_n = int(len(away_rows))
    quality = quality_from_match_counts(home_n, away_n)
    rates = _rates(home_rows, away_rows)
    home_signal = round(rates["home_home_win_rate"] + rates["away_away_loss_rate"], 4)
    draw_signal = round(rates["home_home_draw_rate"] + rates["away_away_draw_rate"], 4)
    away_signal = round(rates["away_away_win_rate"] + rates["home_home_loss_rate"], 4)
    signals = {"HOME": home_signal, "DRAW": draw_signal, "AWAY": away_signal}
    top, top_value = max(signals.items(), key=lambda item: item[1])
    second = sorted(signals.values(), reverse=True)[1]
    edge = round(top_value - second, 4)
    strength = min(0.04, edge * 0.08) if quality != "LOW" and edge >= 0.15 else 0.0
    adjusted = None
    if strength and top == "HOME":
        adjusted = apply_home_away_shift(base_home_probability, base_draw_probability, base_away_probability, strength)
    elif strength and top == "AWAY":
        adjusted = apply_home_away_shift(base_home_probability, base_draw_probability, base_away_probability, -strength)
    elif strength and top == "DRAW":
        adjusted = preserve_home_away_ratio_adjust_draw(base_home_probability, base_draw_probability, base_away_probability, strength)
    reason = "LOW quality venue result rate; no adjustment" if quality == "LOW" else ("Venue result signals too close; no adjustment" if not strength else f"Venue result profile shifted diagnostic probability toward {top}")
    result = build_shadow_result_dict("vr", "VENUE_RESULT_RATE", quality, reason, base_home_probability, base_draw_probability, base_away_probability, adjusted, strength, bool(strength), reason)
    result.update({f"vr_{key}": value for key, value in rates.items()})
    result.update({"vr_home_signal": home_signal, "vr_draw_signal": draw_signal, "vr_away_signal": away_signal, "vr_signal_edge": edge})
    return result


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    return load_match_rows(competition, season, home_team, away_team, match_date, "v2104_venue_result_rate", cache_only=cache_only, enable_network=enable_network)


def _rates(home_rows: pd.DataFrame, away_rows: pd.DataFrame) -> dict[str, float]:
    home_n = len(home_rows)
    away_n = len(away_rows)
    home_win = int(home_rows["home_goals"].astype(float).gt(home_rows["away_goals"].astype(float)).sum()) if home_n else 0
    home_draw = int(home_rows["home_goals"].astype(float).eq(home_rows["away_goals"].astype(float)).sum()) if home_n else 0
    home_loss = home_n - home_win - home_draw
    away_win = int(away_rows["away_goals"].astype(float).gt(away_rows["home_goals"].astype(float)).sum()) if away_n else 0
    away_draw = int(away_rows["away_goals"].astype(float).eq(away_rows["home_goals"].astype(float)).sum()) if away_n else 0
    away_loss = away_n - away_win - away_draw
    return {
        "home_home_win_rate": round(home_win / home_n, 4) if home_n else 0.0,
        "home_home_draw_rate": round(home_draw / home_n, 4) if home_n else 0.0,
        "home_home_loss_rate": round(home_loss / home_n, 4) if home_n else 0.0,
        "away_away_win_rate": round(away_win / away_n, 4) if away_n else 0.0,
        "away_away_draw_rate": round(away_draw / away_n, 4) if away_n else 0.0,
        "away_away_loss_rate": round(away_loss / away_n, 4) if away_n else 0.0,
    }


def _empty(base_home: float, base_draw: float, base_away: float, reason: str) -> dict[str, object]:
    result = build_shadow_result_dict("vr", "VENUE_RESULT_RATE", "LOW", reason, base_home, base_draw, base_away, None, 0.0, False, reason)
    result.update({f"vr_{key}": 0.0 for key in ["home_home_win_rate", "home_home_draw_rate", "home_home_loss_rate", "away_away_win_rate", "away_away_draw_rate", "away_away_loss_rate", "home_signal", "draw_signal", "away_signal", "signal_edge"]})
    return result
