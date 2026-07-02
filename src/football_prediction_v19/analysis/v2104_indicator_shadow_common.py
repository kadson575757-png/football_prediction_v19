# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pandas as pd

from football_prediction_v19.analysis.v20_football_data_live_adapter import run_football_data_live_adapter
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context, normalize_match_date
from football_prediction_v19.analysis.v20_source_league_resolver import resolve_source_league
from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league


def normalize_probabilities(home: object, draw: object, away: object) -> tuple[float, float, float]:
    values = [max(0.0, _num(home)), max(0.0, _num(draw)), max(0.0, _num(away))]
    total = sum(values)
    if total <= 0:
        return 0.34, 0.32, 0.34
    home_p = round(values[0] / total, 4)
    draw_p = round(values[1] / total, 4)
    away_p = round(max(0.0, 1.0 - home_p - draw_p), 4)
    return home_p, draw_p, away_p


def preserve_home_away_ratio_adjust_draw(base_home: object, base_draw: object, base_away: object, draw_shift: float) -> tuple[float, float, float]:
    home, draw, away = normalize_probabilities(base_home, base_draw, base_away)
    adjusted_draw = min(0.80, max(0.05, draw + draw_shift))
    remaining = max(0.02, 1.0 - adjusted_draw)
    ha_total = home + away
    if ha_total <= 0:
        return normalize_probabilities(remaining / 2, adjusted_draw, remaining / 2)
    return normalize_probabilities(remaining * home / ha_total, adjusted_draw, remaining * away / ha_total)


def apply_home_away_shift(base_home: object, base_draw: object, base_away: object, home_shift: float) -> tuple[float, float, float]:
    home, draw, away = normalize_probabilities(base_home, base_draw, base_away)
    return normalize_probabilities(max(0.01, home + home_shift), draw, max(0.01, away - home_shift))


def quality_from_match_counts(home_count: int, away_count: int) -> str:
    if home_count >= 8 and away_count >= 8:
        return "FULL"
    if home_count >= 3 and away_count >= 3:
        return "PARTIAL"
    return "LOW"


def build_shadow_result_dict(
    prefix: str,
    indicator_name: str,
    quality: str,
    reason: str,
    base_home: object,
    base_draw: object,
    base_away: object,
    adjusted: tuple[float, float, float] | None,
    strength: float,
    applied: bool,
    explanation: str,
) -> dict[str, object]:
    home, draw, away = normalize_probabilities(base_home, base_draw, base_away) if adjusted is None else adjusted
    return {
        "indicator_name": indicator_name,
        "indicator_quality": quality,
        "indicator_reason": reason,
        "adjustment_applied": bool(applied),
        "adjustment_strength": round(float(strength), 4),
        "adjusted_home_win_probability": round(home, 4),
        "adjusted_draw_probability": round(draw, 4),
        "adjusted_away_probability": round(away, 4),
        "explanation": explanation,
        f"{prefix}_indicator_quality": quality,
        f"{prefix}_indicator_reason": reason,
        f"{prefix}_adjusted_home_win_probability": round(home, 4),
        f"{prefix}_adjusted_draw_probability": round(draw, 4),
        f"{prefix}_adjusted_away_probability": round(away, 4),
        f"{prefix}_adjustment_applied": bool(applied),
        f"{prefix}_adjustment_strength": round(float(strength), 4),
        f"{prefix}_adjustment_reason": reason,
        f"{prefix}_shadow_explanation": explanation,
    }


def load_match_rows(
    competition: str,
    season: str,
    home_team: str,
    away_team: str,
    match_date: str,
    output_slug: str,
    *,
    cache_only: bool,
    enable_network: bool,
) -> pd.DataFrame:
    out = Path("outputs") / output_slug / _slug(f"{competition}_{season}_{home_team}_vs_{away_team}")
    mapping = resolve_source_league(competition, season, out / "mapping")
    context = build_match_context(home_team, away_team, competition, season, match_date)
    live = run_football_data_live_adapter(
        mapping,
        context,
        out / "football_data",
        enable_network=bool(enable_network and not cache_only),
        cache_dir=Path("outputs/cache/v20_live_sources"),
    )
    path = Path(str(live.get("football_data_live_normalized_path", "")))
    if not path.exists():
        return pd.DataFrame()
    frame = pd.read_csv(path, keep_default_na=False)
    rows = []
    for _, row in frame.iterrows():
        try:
            date = normalize_match_date(str(row.get("Date", "")))
        except Exception:
            continue
        if str(row.get("FTHG", "")).strip() == "" or str(row.get("FTAG", "")).strip() == "":
            continue
        rows.append(
            {
                "match_date": date,
                "home_team": row.get("HomeTeam", ""),
                "away_team": row.get("AwayTeam", ""),
                "home_goals": int(float(row.get("FTHG", 0))),
                "away_goals": int(float(row.get("FTAG", 0))),
            }
        )
    return pd.DataFrame(rows)


def prior_rows(frame: pd.DataFrame, match_date: str) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    target_date = normalize_match_date(match_date)
    work = frame.copy()
    work["_date"] = work["match_date"].map(_safe_date)
    return work[work["_date"].astype(str).lt(target_date)].copy()


def team_matches(frame: pd.DataFrame, team: str) -> pd.DataFrame:
    team_norm = normalize_team_or_league(team)
    if frame.empty:
        return frame.copy()
    return frame[
        frame["home_team"].map(normalize_team_or_league).eq(team_norm)
        | frame["away_team"].map(normalize_team_or_league).eq(team_norm)
    ].copy()


def venue_matches(frame: pd.DataFrame, team: str, venue: str) -> pd.DataFrame:
    team_norm = normalize_team_or_league(team)
    column = "home_team" if venue == "home" else "away_team"
    if frame.empty:
        return frame.copy()
    return frame[frame[column].map(normalize_team_or_league).eq(team_norm)].copy()


def _safe_date(value: object) -> str:
    try:
        return normalize_match_date(str(value))
    except Exception:
        return ""


def _slug(value: str) -> str:
    return "_".join("".join(ch.lower() if ch.isalnum() else " " for ch in str(value)).split())


def _num(value: object) -> float:
    try:
        if str(value).strip() == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
