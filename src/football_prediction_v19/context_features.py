# -*- coding: utf-8 -*-
"""Context-aware feature engineering for football match predictions.

DIAGNOSTIC / ANALYTICAL LAYER ONLY.
- All features derived from prior data only (no leakage).
- Graceful degradation when columns are absent.
- No betting, ROI, or staking logic.

Public API
----------
compute_table_context(df) -> pd.DataFrame
compute_fatigue_features(df, short_rest_days=4) -> pd.DataFrame
compute_referee_features(df, window=20) -> pd.DataFrame
compute_rivalry_features(df) -> pd.DataFrame
build_context_features(df, ...) -> pd.DataFrame
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

__all__ = [
    "compute_table_context",
    "compute_fatigue_features",
    "compute_referee_features",
    "compute_rivalry_features",
    "build_context_features",
]

# ---------------------------------------------------------------------------
# Derby / Rivalry registry
# ---------------------------------------------------------------------------

_DERBIES: dict[frozenset[str], str] = {
    frozenset({"Real Madrid", "Barcelona"}):          "El Clasico",
    frozenset({"Atletico Madrid", "Real Madrid"}):    "Der Clasico",
    frozenset({"Borussia Dortmund", "Schalke"}):      "Revierderby",
    frozenset({"Hamburg", "Werder Bremen"}):           "Nordderby",
    frozenset({"Manchester City", "Manchester United"}): "Manchester Derby",
    frozenset({"Liverpool", "Everton"}):               "Merseyside Derby",
    frozenset({"Arsenal", "Tottenham Hotspur"}):       "North London Derby",
    frozenset({"Roma", "Lazio"}):                      "Rome Derby",
    frozenset({"AC Milan", "Inter"}):                  "Milan Derby",
    frozenset({"Juventus", "Torino"}):                 "Turin Derby",
    frozenset({"PSG", "Marseille"}):                   "Paris Derby",
    frozenset({"Ajax", "Feyenoord"}):                  "Amsterdam Derby",
}


# ---------------------------------------------------------------------------
# Task 1 — Table-situation features
# ---------------------------------------------------------------------------

def compute_table_context(df: pd.DataFrame) -> pd.DataFrame:
    """Compute live-table context for each match using only prior data.

    Columns added:
        home_table_rank, away_table_rank,
        home_points, away_points,
        home_relegation_zone, away_relegation_zone,
        home_title_race, away_title_race,
        dead_rubber_flag, rank_diff.

    Values are NaN when fewer than 5 prior matches exist.
    When a ``league`` column is present, the table is computed per league.
    """
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values("date").reset_index(drop=True)

    has_league = "league" in out.columns

    home_rank_col:   list[Any] = []
    away_rank_col:   list[Any] = []
    home_pts_col:    list[Any] = []
    away_pts_col:    list[Any] = []
    home_relz_col:   list[Any] = []
    away_relz_col:   list[Any] = []
    home_title_col:  list[Any] = []
    away_title_col:  list[Any] = []
    dead_rubber_col: list[Any] = []
    rank_diff_col:   list[Any] = []

    for _, row in out.iterrows():
        cutoff    = row["date"]
        home_team = row["home_team"]
        away_team = row["away_team"]
        league    = row.get("league") if has_league else None

        prior = out[out["date"] < cutoff]
        if has_league and pd.notna(league):
            prior = prior[prior["league"] == league]

        if len(prior) < 5:
            for lst in (home_rank_col, away_rank_col, home_pts_col, away_pts_col,
                        home_relz_col, away_relz_col, home_title_col, away_title_col,
                        dead_rubber_col, rank_diff_col):
                lst.append(np.nan)
            continue

        # Build points table
        pts: dict[str, int] = {}
        gd:  dict[str, int] = {}
        gf_total: dict[str, int] = {}

        for _, m in prior.iterrows():
            h = m["home_team"]
            a = m["away_team"]
            hg = int(m["home_goals"])
            ag = int(m["away_goals"])
            for t in (h, a):
                if t not in pts:
                    pts[t] = 0
                    gd[t]  = 0
                    gf_total[t] = 0
            if hg > ag:
                pts[h] += 3
            elif hg == ag:
                pts[h] += 1
                pts[a] += 1
            else:
                pts[a] += 3
            gd[h] += hg - ag
            gd[a] += ag - hg
            gf_total[h] += hg
            gf_total[a] += ag

        # Rank teams: highest pts first, then GD, then GF
        all_teams = sorted(
            pts.keys(),
            key=lambda t: (pts[t], gd[t], gf_total[t]),
            reverse=True,
        )
        rank_map = {t: i + 1 for i, t in enumerate(all_teams)}
        n_teams  = len(all_teams)

        def _rank(team: str) -> "float":
            return float(rank_map.get(team, np.nan))

        def _pts(team: str) -> "float":
            return float(pts.get(team, np.nan))

        hr = _rank(home_team)
        ar = _rank(away_team)
        hp = _pts(home_team)
        ap = _pts(away_team)

        # Relegation / title thresholds
        relz_boundary  = max(n_teams - 2, 1)   # bottom 3
        title_boundary = 3

        home_relz  = bool(pd.notna(hr) and hr >= relz_boundary)
        away_relz  = bool(pd.notna(ar) and ar >= relz_boundary)
        home_title = bool(pd.notna(hr) and hr <= title_boundary)
        away_title = bool(pd.notna(ar) and ar <= title_boundary)

        # Dead rubber: neither team in contention AND gap to 3rd/relz > 10 pts
        if pd.notna(hr) and pd.notna(ar):
            # Points at 3rd place and relegation boundary
            pts_3rd  = float(pts.get(all_teams[min(2, n_teams - 1)], 0))
            pts_relz = float(pts.get(all_teams[relz_boundary - 1], 0)) if relz_boundary <= n_teams else 0.0
            not_in_title = (not home_title) and (not away_title)
            not_in_relz  = (not home_relz)  and (not away_relz)
            gap_to_title = min(hp, ap) - pts_3rd   # negative = behind
            gap_to_relz  = max(hp, ap) - pts_relz  # positive = safe

            dead_rubber = bool(
                not_in_title and not_in_relz
                and gap_to_title < -10
                and gap_to_relz  > 10
            )
        else:
            dead_rubber = False

        rank_diff = (hr - ar) if pd.notna(hr) and pd.notna(ar) else np.nan

        home_rank_col.append(hr)
        away_rank_col.append(ar)
        home_pts_col.append(hp)
        away_pts_col.append(ap)
        home_relz_col.append(home_relz)
        away_relz_col.append(away_relz)
        home_title_col.append(home_title)
        away_title_col.append(away_title)
        dead_rubber_col.append(dead_rubber)
        rank_diff_col.append(rank_diff)

    out["home_table_rank"]      = home_rank_col
    out["away_table_rank"]      = away_rank_col
    out["home_points"]          = home_pts_col
    out["away_points"]          = away_pts_col
    out["home_relegation_zone"] = home_relz_col
    out["away_relegation_zone"] = away_relz_col
    out["home_title_race"]      = home_title_col
    out["away_title_race"]      = away_title_col
    out["dead_rubber_flag"]     = dead_rubber_col
    out["rank_diff"]            = rank_diff_col
    return out


# ---------------------------------------------------------------------------
# Task 2 — Fatigue / rest features
# ---------------------------------------------------------------------------

def compute_fatigue_features(
    df: pd.DataFrame,
    short_rest_days: int = 4,
) -> pd.DataFrame:
    """Compute match-load and rest-interval features using only prior data.

    Columns added:
        home_days_since_last, away_days_since_last,
        home_short_rest, away_short_rest,
        home_games_last_30_days, away_games_last_30_days,
        fatigue_advantage.
    """
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values("date").reset_index(drop=True)

    home_dsl:    list[Any] = []
    away_dsl:    list[Any] = []
    home_sr:     list[Any] = []
    away_sr:     list[Any] = []
    home_g30:    list[int] = []
    away_g30:    list[int] = []
    fatigue_adv: list[str] = []

    for _, row in out.iterrows():
        cutoff    = row["date"]
        home_team = row["home_team"]
        away_team = row["away_team"]

        prior = out[out["date"] < cutoff]

        def _last_match_date(team: str) -> "pd.Timestamp | None":
            h = prior[prior["home_team"] == team]["date"]
            a = prior[prior["away_team"] == team]["date"]
            all_dates = pd.concat([h, a])
            return all_dates.max() if not all_dates.empty else None

        def _days_since(team: str) -> "float":
            lmd = _last_match_date(team)
            if lmd is None or pd.isna(lmd):
                return np.nan
            return float((cutoff - lmd).days)

        def _games_last_n(team: str, days: int = 30) -> int:
            window_start = cutoff - pd.Timedelta(days=days)
            h = prior[(prior["home_team"] == team) & (prior["date"] >= window_start)]
            a = prior[(prior["away_team"] == team) & (prior["date"] >= window_start)]
            return len(h) + len(a)

        h_dsl = _days_since(home_team)
        a_dsl = _days_since(away_team)
        h_sr  = bool(pd.notna(h_dsl) and h_dsl <= short_rest_days)
        a_sr  = bool(pd.notna(a_dsl) and a_dsl <= short_rest_days)
        h_g30 = _games_last_n(home_team)
        a_g30 = _games_last_n(away_team)

        if not h_sr and a_sr:
            adv = "home"
        elif h_sr and not a_sr:
            adv = "away"
        else:
            adv = "none"

        home_dsl.append(h_dsl)
        away_dsl.append(a_dsl)
        home_sr.append(h_sr)
        away_sr.append(a_sr)
        home_g30.append(h_g30)
        away_g30.append(a_g30)
        fatigue_adv.append(adv)

    out["home_days_since_last"]    = home_dsl
    out["away_days_since_last"]    = away_dsl
    out["home_short_rest"]         = home_sr
    out["away_short_rest"]         = away_sr
    out["home_games_last_30_days"] = home_g30
    out["away_games_last_30_days"] = away_g30
    out["fatigue_advantage"]       = fatigue_adv
    return out


# ---------------------------------------------------------------------------
# Task 3 — Referee features
# ---------------------------------------------------------------------------

def compute_referee_features(
    df: pd.DataFrame,
    window: int = 20,
) -> pd.DataFrame:
    """Compute referee-style statistics using only prior matches refereed.

    Returns *df* unchanged (silently) if no ``referee`` column is present.

    Columns added:
        ref_avg_goals, ref_btts_rate, ref_cards_per_game,
        ref_over25_rate, ref_n.
    """
    if "referee" not in df.columns:
        return df

    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values("date").reset_index(drop=True)

    has_cards = "yellow_cards" in out.columns or "red_cards" in out.columns

    ref_avg_goals:   list[Any] = []
    ref_btts_rate:   list[Any] = []
    ref_cards:       list[Any] = []
    ref_over25_rate: list[Any] = []
    ref_n_col:       list[int] = []

    for _, row in out.iterrows():
        cutoff = row["date"]
        ref    = row.get("referee")

        if pd.isna(ref) or ref == "":
            ref_avg_goals.append(np.nan)
            ref_btts_rate.append(np.nan)
            ref_cards.append(np.nan)
            ref_over25_rate.append(np.nan)
            ref_n_col.append(0)
            continue

        prior_ref = out[
            (out["date"] < cutoff) & (out["referee"] == ref)
        ].tail(window)

        n = len(prior_ref)
        ref_n_col.append(n)

        if n < 3:
            ref_avg_goals.append(np.nan)
            ref_btts_rate.append(np.nan)
            ref_cards.append(np.nan)
            ref_over25_rate.append(np.nan)
            continue

        total_goals = (prior_ref["home_goals"] + prior_ref["away_goals"])
        btts_mask   = (prior_ref["home_goals"] >= 1) & (prior_ref["away_goals"] >= 1)

        ref_avg_goals.append(float(total_goals.mean()))
        ref_btts_rate.append(float(btts_mask.mean()))
        ref_over25_rate.append(float((total_goals > 2.5).mean()))

        if has_cards:
            cards = pd.Series(0.0, index=prior_ref.index)
            if "yellow_cards" in prior_ref.columns:
                cards = cards + prior_ref["yellow_cards"].fillna(0)
            if "red_cards" in prior_ref.columns:
                cards = cards + prior_ref["red_cards"].fillna(0)
            ref_cards.append(float(cards.mean()))
        else:
            ref_cards.append(np.nan)

    out["ref_avg_goals"]   = ref_avg_goals
    out["ref_btts_rate"]   = ref_btts_rate
    out["ref_cards_per_game"] = ref_cards
    out["ref_over25_rate"] = ref_over25_rate
    out["ref_n"]           = ref_n_col
    return out


# ---------------------------------------------------------------------------
# Task 4 — Derby / Rivalry flag
# ---------------------------------------------------------------------------

def compute_rivalry_features(df: pd.DataFrame) -> pd.DataFrame:
    """Flag known derbies and rivalries.

    Columns added:
        is_derby (bool), derby_name (str or "").
    """
    out = df.copy()
    is_derby_col:   list[bool] = []
    derby_name_col: list[str]  = []

    for _, row in out.iterrows():
        pair = frozenset({row["home_team"], row["away_team"]})
        name = _DERBIES.get(pair, "")
        is_derby_col.append(name != "")
        derby_name_col.append(name)

    out["is_derby"]   = is_derby_col
    out["derby_name"] = derby_name_col
    return out


# ---------------------------------------------------------------------------
# Task 5 — Context pipeline
# ---------------------------------------------------------------------------

def build_context_features(
    df: pd.DataFrame,
    include_table:   bool = True,
    include_fatigue: bool = True,
    include_referee: bool = True,
    include_rivalry: bool = True,
) -> pd.DataFrame:
    """Run all context feature modules in order.

    Idempotent: never overwrites columns already present in *df*.
    Gracefully skips modules when required columns are absent.

    Parameters
    ----------
    df:
        Match DataFrame with at minimum: date, home_team, away_team,
        home_goals, away_goals.
    include_table, include_fatigue, include_referee, include_rivalry:
        Flags to enable/disable individual modules.

    Returns
    -------
    pd.DataFrame with all requested new columns appended.
    """
    existing_cols = set(df.columns)
    out = df.copy()

    def _safe_merge(new_df: pd.DataFrame) -> pd.DataFrame:
        new_cols = [c for c in new_df.columns
                    if c not in existing_cols and c not in out.columns]
        if new_cols:
            # Align on index
            return out.join(new_df[new_cols].set_index(new_df.index), how="left")
        return out

    if include_table:
        try:
            enriched = compute_table_context(out)
            out = _safe_merge(enriched)
        except Exception:
            pass

    if include_fatigue:
        try:
            enriched = compute_fatigue_features(out)
            out = _safe_merge(enriched)
        except Exception:
            pass

    if include_referee:
        try:
            enriched = compute_referee_features(out)
            out = _safe_merge(enriched)
        except Exception:
            pass

    if include_rivalry:
        try:
            enriched = compute_rivalry_features(out)
            out = _safe_merge(enriched)
        except Exception:
            pass

    return out
