from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
import pandas as pd

from .data import clean_matches

WINDOWS = (5, 10)

ROLLING_OPTIONAL_METRICS = [
    "shots",
    "shots_on_target",
    "big_chances",
    "possession",
    "ppda",
    "rest_days",
    "injuries_count",
    "market_value",
]


def _safe_mean(values: list[float]) -> float:
    values = [v for v in values if pd.notna(v)]
    if not values:
        return np.nan
    return float(np.mean(values))


def _safe_sum(values: list[float]) -> float:
    values = [v for v in values if pd.notna(v)]
    if not values:
        return np.nan
    return float(np.sum(values))


def _points(gf: float, ga: float) -> int:
    if gf > ga:
        return 3
    if gf == ga:
        return 1
    return 0


def _side_value(row: pd.Series, side: str, metric: str, fallback: float = np.nan) -> float:
    value = row.get(f"{side}_{metric}", fallback)
    return float(value) if pd.notna(value) else fallback


def _entry(team: str, opponent: str, venue_side: str, row: pd.Series) -> dict[str, Any]:
    is_home = venue_side == "home"
    side = "home" if is_home else "away"
    opp_side = "away" if is_home else "home"
    gf = float(row["home_goals"] if is_home else row["away_goals"])
    ga = float(row["away_goals"] if is_home else row["home_goals"])
    xgf = float(row["home_xg"] if is_home else row["away_xg"])
    xga = _side_value(row, side, "xga", float(row["away_xg"] if is_home else row["home_xg"]))
    pts = _points(gf, ga)
    entry = {
        "date": row["date"],
        "team": team,
        "opponent": opponent,
        "venue_side": venue_side,
        "gf": gf,
        "ga": ga,
        "xgf": xgf,
        "xga": xga,
        "points": pts,
        "win": 1 if pts == 3 else 0,
        "draw": 1 if pts == 1 else 0,
        "loss": 1 if pts == 0 else 0,
    }
    for metric in ROLLING_OPTIONAL_METRICS:
        entry[metric] = _side_value(row, side, metric)
        entry[f"opp_{metric}"] = _side_value(row, opp_side, metric)
    return entry


def _history_features(history: list[dict[str, Any]], prefix: str, windows: Iterable[int] = WINDOWS, venue_filter: str | None = None) -> dict[str, float]:
    if venue_filter is not None:
        hist = [h for h in history if h["venue_side"] == venue_filter]
    else:
        hist = list(history)

    feats: dict[str, float] = {}
    feats[f"{prefix}_matches_available"] = float(len(hist))
    if hist:
        last_date = max(h["date"] for h in hist if pd.notna(h["date"]))
        feats[f"{prefix}_days_since_last"] = np.nan
    else:
        feats[f"{prefix}_days_since_last"] = np.nan

    for w in windows:
        recent = hist[-w:]
        n = len(recent)
        base = f"{prefix}_w{w}"
        feats[f"{base}_matches"] = float(n)
        feats[f"{base}_gf"] = _safe_mean([h["gf"] for h in recent])
        feats[f"{base}_ga"] = _safe_mean([h["ga"] for h in recent])
        feats[f"{base}_xgf"] = _safe_mean([h["xgf"] for h in recent])
        feats[f"{base}_xga"] = _safe_mean([h["xga"] for h in recent])
        feats[f"{base}_xgdiff"] = _safe_mean([h["xgf"] - h["xga"] for h in recent])
        feats[f"{base}_goaldiff"] = _safe_mean([h["gf"] - h["ga"] for h in recent])
        feats[f"{base}_ppg"] = _safe_mean([h["points"] for h in recent])
        feats[f"{base}_win_rate"] = _safe_mean([h["win"] for h in recent])
        feats[f"{base}_draw_rate"] = _safe_mean([h["draw"] for h in recent])
        feats[f"{base}_loss_rate"] = _safe_mean([h["loss"] for h in recent])
        for metric in ROLLING_OPTIONAL_METRICS:
            feats[f"{base}_{metric}"] = _safe_mean([h.get(metric, np.nan) for h in recent])
            feats[f"{base}_opp_{metric}"] = _safe_mean([h.get(f"opp_{metric}", np.nan) for h in recent])
    return feats


def _days_since(history: list[dict[str, Any]], match_date: pd.Timestamp) -> float:
    if not history or pd.isna(match_date):
        return np.nan
    dates = [h["date"] for h in history if pd.notna(h["date"]) and h["date"] < match_date]
    if not dates:
        return np.nan
    return float((match_date - max(dates)).days)


def _add_match_context(row: pd.Series) -> dict[str, Any]:
    feats: dict[str, Any] = {
        "matchweek": row.get("matchweek", np.nan),
        "home_team": row.get("home_team", "Unknown"),
        "away_team": row.get("away_team", "Unknown"),
        "venue": row.get("venue", "Unknown"),
        "referee": row.get("referee", "Unknown"),
        "day_name": row.get("day_name", "Unknown"),
        "season_start": row.get("season_start", np.nan),
    }
    for c in [
        "odds_home", "odds_draw", "odds_away",
        "odds_home_open", "odds_draw_open", "odds_away_open",
        "formation_home_xg90", "formation_away_xg90",
        "set_piece_xg_ratio_home", "set_piece_xg_ratio_away",
        "fatigue_home", "fatigue_away",
        "home_rest_days", "away_rest_days",
        "home_injuries_count", "away_injuries_count",
        "home_market_value", "away_market_value",
    ]:
        if c in row.index:
            feats[c] = row.get(c, np.nan)
    return feats


def _market_features(feats: dict[str, Any]) -> None:
    odds_cols = ["odds_home", "odds_draw", "odds_away"]
    if all(c in feats and pd.notna(feats[c]) and float(feats[c]) > 1 for c in odds_cols):
        raw = {k: 1.0 / float(feats[k]) for k in odds_cols}
        overround = sum(raw.values())
        feats["market_prob_home"] = raw["odds_home"] / overround
        feats["market_prob_draw"] = raw["odds_draw"] / overround
        feats["market_prob_away"] = raw["odds_away"] / overround
        feats["market_overround"] = overround - 1.0
    else:
        feats["market_prob_home"] = np.nan
        feats["market_prob_draw"] = np.nan
        feats["market_prob_away"] = np.nan
        feats["market_overround"] = np.nan

    for side in ["home", "draw", "away"]:
        c = f"odds_{side}"
        o = f"odds_{side}_open"
        if c in feats and o in feats and pd.notna(feats[c]) and pd.notna(feats[o]) and float(feats[o]) > 0:
            feats[f"market_move_{side}"] = (float(feats[o]) - float(feats[c])) / float(feats[o])
        else:
            feats[f"market_move_{side}"] = np.nan


def _feature_row(row: pd.Series, histories: dict[str, list[dict[str, Any]]], windows: Iterable[int] = WINDOWS) -> dict[str, Any]:
    home = row["home_team"]
    away = row["away_team"]
    home_hist = histories.get(home, [])
    away_hist = histories.get(away, [])
    match_date = row["date"]

    feats = _add_match_context(row)
    feats.update(_history_features(home_hist, "home", windows=windows))
    feats.update(_history_features(away_hist, "away", windows=windows))
    feats.update(_history_features(home_hist, "home_home", windows=windows, venue_filter="home"))
    feats.update(_history_features(away_hist, "away_away", windows=windows, venue_filter="away"))
    feats["home_days_since_last"] = _days_since(home_hist, match_date)
    feats["away_days_since_last"] = _days_since(away_hist, match_date)

    for w in windows:
        feats[f"edge_w{w}_xgf_vs_xga"] = feats.get(f"home_w{w}_xgf", np.nan) - feats.get(f"away_w{w}_xga", np.nan)
        feats[f"edge_w{w}_away_xgf_vs_home_xga"] = feats.get(f"away_w{w}_xgf", np.nan) - feats.get(f"home_w{w}_xga", np.nan)
        feats[f"edge_w{w}_xgdiff"] = feats.get(f"home_w{w}_xgdiff", np.nan) - feats.get(f"away_w{w}_xgdiff", np.nan)
        feats[f"edge_w{w}_ppg"] = feats.get(f"home_w{w}_ppg", np.nan) - feats.get(f"away_w{w}_ppg", np.nan)
        feats[f"edge_w{w}_shots"] = feats.get(f"home_w{w}_shots", np.nan) - feats.get(f"away_w{w}_shots", np.nan)
        feats[f"edge_w{w}_shots_on_target"] = feats.get(f"home_w{w}_shots_on_target", np.nan) - feats.get(f"away_w{w}_shots_on_target", np.nan)
        feats[f"edge_w{w}_big_chances"] = feats.get(f"home_w{w}_big_chances", np.nan) - feats.get(f"away_w{w}_big_chances", np.nan)
        feats[f"edge_w{w}_rest_days"] = feats.get(f"home_w{w}_rest_days", np.nan) - feats.get(f"away_w{w}_rest_days", np.nan)
        feats[f"edge_w{w}_injuries_count"] = feats.get(f"away_w{w}_injuries_count", np.nan) - feats.get(f"home_w{w}_injuries_count", np.nan)
        feats[f"expected_total_xg_w{w}"] = feats.get(f"home_w{w}_xgf", np.nan) + feats.get(f"away_w{w}_xgf", np.nan)

    _market_features(feats)
    return feats


def build_features(df: pd.DataFrame, windows: Iterable[int] = WINDOWS, min_history: int = 1) -> pd.DataFrame:
    """Build a training table without leakage.

    Each row uses only matches played before that row's match date.
    """
    matches = clean_matches(df, completed_only=True)
    histories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rows: list[dict[str, Any]] = []

    for _, row in matches.iterrows():
        feats = _feature_row(row, histories, windows)
        feats["date"] = row["date"]
        feats["league"] = row.get("league", "Unknown")
        feats["score"] = row["score"]
        feats["home_goals"] = row["home_goals"]
        feats["away_goals"] = row["away_goals"]
        feats["home_xg"] = row["home_xg"]
        feats["away_xg"] = row["away_xg"]
        feats["actual_total_goals"] = row["actual_total_goals"]
        feats["actual_goal_diff"] = row["actual_goal_diff"]
        feats["result"] = row["result"]
        rows.append(feats)

        histories[row["home_team"]].append(_entry(row["home_team"], row["away_team"], "home", row))
        histories[row["away_team"]].append(_entry(row["away_team"], row["home_team"], "away", row))

    out = pd.DataFrame(rows)
    enough_history = (out["home_matches_available"] >= min_history) & (out["away_matches_available"] >= min_history)
    out = out.loc[enough_history].reset_index(drop=True)
    return out


def build_fixture_features(
    history_df: pd.DataFrame,
    home_team: str,
    away_team: str,
    match_date: str | pd.Timestamp,
    venue: str = "Unknown",
    referee: str = "Unknown",
    matchweek: int | float | None = None,
    odds_home: float | None = None,
    odds_draw: float | None = None,
    odds_away: float | None = None,
    extra: dict[str, Any] | None = None,
    windows: Iterable[int] = WINDOWS,
) -> pd.DataFrame:
    history = clean_matches(history_df, completed_only=True)
    match_date = pd.to_datetime(match_date)
    history = history[history["date"] < match_date].sort_values("date")
    histories: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for _, row in history.iterrows():
        histories[row["home_team"]].append(_entry(row["home_team"], row["away_team"], "home", row))
        histories[row["away_team"]].append(_entry(row["away_team"], row["home_team"], "away", row))

    row_data: dict[str, Any] = {
        "date": match_date,
        "matchweek": matchweek if matchweek is not None else np.nan,
        "home_team": home_team,
        "away_team": away_team,
        "venue": venue,
        "referee": referee,
        "day_name": match_date.day_name(),
        "season_start": int(match_date.year) if (extra or {}).get("league") == "MLS"
        else int(match_date.year - 1 if match_date.month < 8 else match_date.year),
    }
    if odds_home is not None:
        row_data["odds_home"] = odds_home
    if odds_draw is not None:
        row_data["odds_draw"] = odds_draw
    if odds_away is not None:
        row_data["odds_away"] = odds_away
    if extra:
        row_data.update(extra)

    row = pd.Series(row_data)
    feats = _feature_row(row, histories, windows)
    feats["date"] = match_date
    return pd.DataFrame([feats])


# ---------------------------------------------------------------------------
# Phase-5 Feature Engineering
# ---------------------------------------------------------------------------

import math as _math


def compute_opponent_adjusted_xg(
    df: pd.DataFrame,
    window: int = 10,
) -> pd.DataFrame:
    """Compute opponent-adjusted xG for each match using only prior data.

    For each match, the home/away xG is scaled by the opponent's recent
    defensive strength (mean xG conceded per game over the last *window*
    matches), so a goal scored against a leaky defence is discounted.

    New columns added:
        ``adj_home_xg``, ``adj_away_xg``,
        ``opponent_strength_home``, ``opponent_strength_away``.

    Returns *df* unchanged (with a print warning) if xG columns are absent.
    """
    xg_cols = {"home_xg", "away_xg"}
    if not xg_cols.issubset(df.columns):
        print("xG columns not found, skipping")
        return df

    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values("date").reset_index(drop=True)

    adj_home_xg:      list[float] = []
    adj_away_xg:      list[float] = []
    opp_str_home:     list[float] = []
    opp_str_away:     list[float] = []

    for i, row in out.iterrows():
        cutoff = row["date"]
        prior  = out[out["date"] < cutoff]

        home_team = row["home_team"]
        away_team = row["away_team"]

        # xG conceded by away_team (as home or away) in prior window matches
        away_as_home = prior[prior["home_team"] == away_team]["away_xg"].dropna()
        away_as_away = prior[prior["away_team"] == away_team]["home_xg"].dropna()
        away_conceded = pd.concat([away_as_home, away_as_away]).tail(window)
        opp_str_h = float(away_conceded.mean()) if len(away_conceded) > 0 else np.nan

        # xG conceded by home_team
        home_as_home = prior[prior["home_team"] == home_team]["away_xg"].dropna()
        home_as_away = prior[prior["away_team"] == home_team]["home_xg"].dropna()
        home_conceded = pd.concat([home_as_home, home_as_away]).tail(window)
        opp_str_a = float(home_conceded.mean()) if len(home_conceded) > 0 else np.nan

        raw_h = float(row["home_xg"]) if pd.notna(row["home_xg"]) else np.nan
        raw_a = float(row["away_xg"]) if pd.notna(row["away_xg"]) else np.nan

        adj_h = raw_h / (opp_str_a + 0.01) if pd.notna(raw_h) and pd.notna(opp_str_a) else np.nan
        adj_a = raw_a / (opp_str_h + 0.01) if pd.notna(raw_a) and pd.notna(opp_str_h) else np.nan

        adj_home_xg.append(adj_h)
        adj_away_xg.append(adj_a)
        opp_str_home.append(opp_str_h)
        opp_str_away.append(opp_str_a)

    out["adj_home_xg"]            = adj_home_xg
    out["adj_away_xg"]            = adj_away_xg
    out["opponent_strength_home"] = opp_str_home
    out["opponent_strength_away"] = opp_str_away
    return out


def compute_time_decay_features(
    df: pd.DataFrame,
    half_life_days: int = 60,
) -> pd.DataFrame:
    """Compute exponentially time-decayed rolling features for each team.

    Uses only prior data (date < current match date).  Requires at least
    3 prior matches per team; otherwise all new columns are NaN for that row.

    New columns added (home_ and away_ prefixed):
        ``td_goals_scored``, ``td_goals_conceded``,
        ``td_xg`` (if home_xg present), ``td_xga`` (if away_xg present),
        ``td_win_rate``.
    """
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values("date").reset_index(drop=True)

    has_xg = "home_xg" in out.columns and "away_xg" in out.columns
    decay = _math.log(2) / half_life_days

    def _weighted_mean(values: list[float], weights: list[float]) -> float:
        pairs = [(v, w) for v, w in zip(values, weights) if pd.notna(v)]
        if not pairs:
            return np.nan
        vs, ws = zip(*pairs)
        return float(np.average(vs, weights=ws))

    def _team_td(team: str, cutoff: pd.Timestamp) -> dict[str, float]:
        """Return time-decay stats for *team* using matches before *cutoff*."""
        rows_h = out[(out["home_team"] == team) & (out["date"] < cutoff)]
        rows_a = out[(out["away_team"] == team) & (out["date"] < cutoff)]

        entries: list[tuple[pd.Timestamp, float, float, float | None, float | None, float]] = []
        for _, r in rows_h.iterrows():
            gf = float(r["home_goals"]) if pd.notna(r.get("home_goals")) else np.nan
            ga = float(r["away_goals"]) if pd.notna(r.get("away_goals")) else np.nan
            xgf = float(r["home_xg"])  if has_xg and pd.notna(r.get("home_xg")) else None
            xga = float(r["away_xg"])  if has_xg and pd.notna(r.get("away_xg")) else None
            win = 1.0 if pd.notna(gf) and pd.notna(ga) and gf > ga else 0.0
            entries.append((r["date"], gf, ga, xgf, xga, win))
        for _, r in rows_a.iterrows():
            gf = float(r["away_goals"]) if pd.notna(r.get("away_goals")) else np.nan
            ga = float(r["home_goals"]) if pd.notna(r.get("home_goals")) else np.nan
            xgf = float(r["away_xg"])  if has_xg and pd.notna(r.get("away_xg")) else None
            xga = float(r["home_xg"])  if has_xg and pd.notna(r.get("home_xg")) else None
            win = 1.0 if pd.notna(gf) and pd.notna(ga) and gf > ga else 0.0
            entries.append((r["date"], gf, ga, xgf, xga, win))

        if len(entries) < 3:
            return {k: np.nan for k in (
                "td_goals_scored", "td_goals_conceded",
                "td_xg", "td_xga", "td_win_rate"
            )}

        weights = [
            _math.exp(-decay * max((cutoff - e[0]).days, 0))
            for e in entries
        ]
        gfs  = [e[1] for e in entries]
        gas  = [e[2] for e in entries]
        xgfs = [e[3] if e[3] is not None else np.nan for e in entries]
        xgas = [e[4] if e[4] is not None else np.nan for e in entries]
        wins = [e[5] for e in entries]

        return {
            "td_goals_scored":   _weighted_mean(gfs,  weights),
            "td_goals_conceded": _weighted_mean(gas,  weights),
            "td_xg":             _weighted_mean(xgfs, weights) if has_xg else np.nan,
            "td_xga":            _weighted_mean(xgas, weights) if has_xg else np.nan,
            "td_win_rate":       _weighted_mean(wins, weights),
        }

    home_rows: list[dict] = []
    away_rows: list[dict] = []

    for _, row in out.iterrows():
        cutoff = row["date"]
        home_rows.append(_team_td(row["home_team"], cutoff))
        away_rows.append(_team_td(row["away_team"], cutoff))

    td_cols = ["td_goals_scored", "td_goals_conceded", "td_xg", "td_xga", "td_win_rate"]
    for col in td_cols:
        out[f"home_{col}"] = [r[col] for r in home_rows]
        out[f"away_{col}"] = [r[col] for r in away_rows]

    return out


def compute_h2h_features(
    df: pd.DataFrame,
    window: int = 5,
) -> pd.DataFrame:
    """Compute head-to-head history features using only prior data.

    New columns added:
        ``h2h_home_wins``, ``h2h_away_wins``, ``h2h_draws``,
        ``h2h_avg_goals``, ``h2h_btts_rate``, ``h2h_n``.

    When ``h2h_n == 0``, all value columns are NaN.
    """
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values("date").reset_index(drop=True)

    h2h_home_wins: list[float] = []
    h2h_away_wins: list[float] = []
    h2h_draws:     list[float] = []
    h2h_avg_goals: list[float] = []
    h2h_btts_rate: list[float] = []
    h2h_n:         list[int]   = []

    for _, row in out.iterrows():
        cutoff    = row["date"]
        home_team = row["home_team"]
        away_team = row["away_team"]

        prior = out[out["date"] < cutoff]
        mask = (
            ((prior["home_team"] == home_team) & (prior["away_team"] == away_team))
            | ((prior["home_team"] == away_team) & (prior["away_team"] == home_team))
        )
        h2h = prior[mask].tail(window)
        n = len(h2h)
        h2h_n.append(n)

        if n == 0:
            h2h_home_wins.append(np.nan)
            h2h_away_wins.append(np.nan)
            h2h_draws.append(np.nan)
            h2h_avg_goals.append(np.nan)
            h2h_btts_rate.append(np.nan)
            continue

        home_wins = draws = away_wins = 0
        total_goals = 0.0
        btts_count  = 0

        for _, m in h2h.iterrows():
            hg = int(m["home_goals"])
            ag = int(m["away_goals"])
            total_goals += hg + ag
            if hg > ag:
                home_wins += 1
            elif hg == ag:
                draws += 1
            else:
                away_wins += 1
            if hg >= 1 and ag >= 1:
                btts_count += 1

        h2h_home_wins.append(home_wins / n)
        h2h_away_wins.append(away_wins / n)
        h2h_draws.append(draws / n)
        h2h_avg_goals.append(total_goals / n)
        h2h_btts_rate.append(btts_count / n)

    out["h2h_home_wins"] = h2h_home_wins
    out["h2h_away_wins"] = h2h_away_wins
    out["h2h_draws"]     = h2h_draws
    out["h2h_avg_goals"] = h2h_avg_goals
    out["h2h_btts_rate"] = h2h_btts_rate
    out["h2h_n"]         = h2h_n
    return out


def compute_game_state_features(
    df: pd.DataFrame,
    window: int = 10,
) -> pd.DataFrame:
    """Compute game-state proxy features from prior match outcomes.

    Uses only data before each match (no leakage).

    New columns added (home_ and away_ prefixed):
        ``lead_rate``, ``comeback_rate``,
        ``clean_sheet_rate``, ``failed_to_score_rate``.

    Values are NaN when fewer than 3 prior matches are available.
    """
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values("date").reset_index(drop=True)

    def _team_state(team: str, cutoff: pd.Timestamp) -> dict[str, float]:
        rows_h = out[(out["home_team"] == team) & (out["date"] < cutoff)].tail(window)
        rows_a = out[(out["away_team"] == team) & (out["date"] < cutoff)].tail(window)

        entries: list[dict] = []
        for _, r in rows_h.iterrows():
            entries.append({
                "gf": int(r["home_goals"]),
                "ga": int(r["away_goals"]),
            })
        for _, r in rows_a.iterrows():
            entries.append({
                "gf": int(r["away_goals"]),
                "ga": int(r["home_goals"]),
            })

        if len(entries) < 3:
            return {k: np.nan for k in (
                "lead_rate", "comeback_rate",
                "clean_sheet_rate", "failed_to_score_rate"
            )}

        n = len(entries)
        leads      = sum(1 for e in entries if e["gf"] > e["ga"])
        comebacks  = sum(1 for e in entries if e["gf"] > 0 and e["ga"] > e["gf"])
        clean      = sum(1 for e in entries if e["ga"] == 0)
        failed     = sum(1 for e in entries if e["gf"] == 0)

        return {
            "lead_rate":            leads     / n,
            "comeback_rate":        comebacks / n,
            "clean_sheet_rate":     clean     / n,
            "failed_to_score_rate": failed    / n,
        }

    gs_cols = ["lead_rate", "comeback_rate", "clean_sheet_rate", "failed_to_score_rate"]
    home_gs: list[dict] = []
    away_gs: list[dict] = []

    for _, row in out.iterrows():
        cutoff = row["date"]
        home_gs.append(_team_state(row["home_team"], cutoff))
        away_gs.append(_team_state(row["away_team"], cutoff))

    for col in gs_cols:
        out[f"home_{col}"] = [r[col] for r in home_gs]
        out[f"away_{col}"] = [r[col] for r in away_gs]

    return out


def build_extended_features(
    df: pd.DataFrame,
    include_elo:        bool = True,
    include_h2h:        bool = True,
    include_time_decay: bool = True,
    include_adj_xg:     bool = True,
    include_game_state: bool = True,
) -> pd.DataFrame:
    """Run all Phase-5 feature engineering in the correct order.

    Idempotent: never overwrites columns already present in *df*.
    Gracefully skips any module whose required input columns are absent.

    Parameters
    ----------
    df:
        Match DataFrame with at minimum: date, home_team, away_team,
        home_goals, away_goals.
    include_elo, include_h2h, include_time_decay,
    include_adj_xg, include_game_state:
        Flags to enable/disable individual feature modules.

    Returns
    -------
    pd.DataFrame with all requested new columns appended.
    """
    from .elo import EloRatingSystem  # lazy import avoids circular issues

    existing_cols = set(df.columns)
    out = df.copy()

    def _safe_merge(new_df: pd.DataFrame) -> pd.DataFrame:
        """Merge new columns into *out*, skipping columns that already exist."""
        new_cols = [c for c in new_df.columns if c not in existing_cols and c not in out.columns]
        if new_cols:
            return out.join(new_df[new_cols], how="left")
        return out

    if include_adj_xg:
        try:
            enriched = compute_opponent_adjusted_xg(out)
            out = _safe_merge(enriched)
        except Exception:
            pass

    if include_time_decay:
        try:
            enriched = compute_time_decay_features(out)
            out = _safe_merge(enriched)
        except Exception:
            pass

    if include_h2h:
        try:
            enriched = compute_h2h_features(out)
            out = _safe_merge(enriched)
        except Exception:
            pass

    if include_game_state:
        try:
            enriched = compute_game_state_features(out)
            out = _safe_merge(enriched)
        except Exception:
            pass

    if include_elo:
        try:
            elo = EloRatingSystem()
            enriched = elo.get_ratings_before_match(out)
            out = _safe_merge(enriched)
        except Exception:
            pass

    return out
