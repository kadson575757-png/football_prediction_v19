# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd

from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league
from football_prediction_v19.analysis.v2104_indicator_shadow_common import apply_home_away_shift, build_shadow_result_dict, load_match_rows, preserve_home_away_ratio_adjust_draw, prior_rows, quality_from_match_counts, team_matches


def build_scoring_run_indicator(
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
    home = _runs(home_rows, home_team)
    away = _runs(away_rows, away_team)
    home_signal = round(home["scored"] + away["conceded"] - home["failed"] - away["clean"], 4)
    away_signal = round(away["scored"] + home["conceded"] - away["failed"] - home["clean"], 4)
    draw_low = round(min(home["failed"], away["failed"]) + min(home["clean"], away["clean"]), 4)
    net = round(home_signal - away_signal, 4)
    strength = 0.0
    adjusted = None
    if quality != "LOW" and draw_low >= 2 and abs(net) <= 2:
        strength = min(0.025, draw_low * 0.006)
        adjusted = preserve_home_away_ratio_adjust_draw(base_home_probability, base_draw_probability, base_away_probability, strength)
    elif quality != "LOW" and abs(net) >= 2:
        strength = min(0.04, abs(net) * 0.006)
        adjusted = apply_home_away_shift(base_home_probability, base_draw_probability, base_away_probability, strength if net > 0 else -strength)
    reason = "LOW quality scoring run profile; no adjustment" if quality == "LOW" else ("Scoring run profile near neutral; no adjustment" if not adjusted else "Scoring run profile shifted diagnostic probability")
    result = build_shadow_result_dict("srp", "SCORING_RUN_PROFILE", quality, reason, base_home_probability, base_draw_probability, base_away_probability, adjusted, strength, bool(strength), reason)
    result.update({
        "srp_home_scored_streak": home["scored"], "srp_home_failed_to_score_streak": home["failed"], "srp_home_conceded_streak": home["conceded"], "srp_home_clean_sheet_streak": home["clean"],
        "srp_away_scored_streak": away["scored"], "srp_away_failed_to_score_streak": away["failed"], "srp_away_conceded_streak": away["conceded"], "srp_away_clean_sheet_streak": away["clean"],
        "srp_home_scoring_run_signal": home_signal, "srp_away_scoring_run_signal": away_signal, "srp_draw_low_score_signal": draw_low,
    })
    return result


def _load_match_rows(competition: str, season: str, home_team: str, away_team: str, match_date: str, *, cache_only: bool, enable_network: bool) -> pd.DataFrame:
    return load_match_rows(competition, season, home_team, away_team, match_date, "v2107_scoring_run", cache_only=cache_only, enable_network=enable_network)


def _runs(frame: pd.DataFrame, team: str) -> dict[str, int]:
    pairs = [_gf_ga(row, team) for _, row in frame.iterrows()]
    return {
        "scored": _tail_count([gf > 0 for gf, _ in pairs], True),
        "failed": _tail_count([gf == 0 for gf, _ in pairs], True),
        "conceded": _tail_count([ga > 0 for _, ga in pairs], True),
        "clean": _tail_count([ga == 0 for _, ga in pairs], True),
    }


def _gf_ga(row: pd.Series, team: str) -> tuple[float, float]:
    team_norm = normalize_team_or_league(team)
    is_home = normalize_team_or_league(row.get("home_team", "")) == team_norm
    return float(row.get("home_goals" if is_home else "away_goals", 0)), float(row.get("away_goals" if is_home else "home_goals", 0))


def _tail_count(values: list[bool], wanted: bool) -> int:
    count = 0
    for value in reversed(values):
        if value is not wanted:
            break
        count += 1
    return count


def _empty(base_home: float, base_draw: float, base_away: float, reason: str) -> dict[str, object]:
    result = build_shadow_result_dict("srp", "SCORING_RUN_PROFILE", "LOW", reason, base_home, base_draw, base_away, None, 0.0, False, reason)
    result.update({"srp_home_scored_streak": 0, "srp_home_failed_to_score_streak": 0, "srp_home_conceded_streak": 0, "srp_home_clean_sheet_streak": 0, "srp_away_scored_streak": 0, "srp_away_failed_to_score_streak": 0, "srp_away_conceded_streak": 0, "srp_away_clean_sheet_streak": 0, "srp_home_scoring_run_signal": 0.0, "srp_away_scoring_run_signal": 0.0, "srp_draw_low_score_signal": 0.0})
    return result
