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

# ── Phase 5 Extended Features ──────────────────────────────────────────────────

import math as _math

def compute_opponent_adjusted_xg(df, window=10):
    import pandas as _pd
    if 'home_xg' not in df.columns or 'away_xg' not in df.columns:
        print("xG columns not found, skipping opponent_adjusted_xg")
        return df
    df = df.copy()
    df['date'] = _pd.to_datetime(df['date'])
    adj_hxg, adj_axg, opp_str_h, opp_str_a = [], [], [], []
    for i in range(len(df)):
        prior = df.iloc[:i]
        home, away = df.iloc[i]['home_team'], df.iloc[i]['away_team']
        def mean_xg_conceded(team, pr):
            games = pr[(pr['home_team']==team)|(pr['away_team']==team)].tail(window)
            if len(games)==0: return 1.0
            vals = []
            for _, r in games.iterrows():
                vals.append(r['away_xg'] if r['home_team']==team else r['home_xg'])
            return float(_pd.Series(vals).mean())
        os_h = mean_xg_conceded(away, prior)
        os_a = mean_xg_conceded(home, prior)
        opp_str_h.append(os_h); opp_str_a.append(os_a)
        adj_hxg.append(df.iloc[i]['home_xg'] / (os_h + 0.01))
        adj_axg.append(df.iloc[i]['away_xg'] / (os_a + 0.01))
    df['adj_home_xg'] = adj_hxg
    df['adj_away_xg'] = adj_axg
    df['opponent_strength_home'] = opp_str_h
    df['opponent_strength_away'] = opp_str_a
    return df


def compute_time_decay_features(df, half_life_days=60):
    import pandas as _pd, numpy as _np
    df = df.copy()
    df['date'] = _pd.to_datetime(df['date'])
    decay = _math.log(2) / half_life_days
    cols = {
        'home_td_goals_scored':[], 'home_td_goals_conceded':[],
        'home_td_xg':[], 'home_td_xga':[], 'home_td_win_rate':[],
        'away_td_goals_scored':[], 'away_td_goals_conceded':[],
        'away_td_xg':[], 'away_td_xga':[], 'away_td_win_rate':[]
    }
    def weighted_mean(values, weights):
        if len(values)==0: return _np.nan
        ws = _np.array(weights); vs = _np.array(values)
        return float((vs*ws).sum() / ws.sum()) if ws.sum()>0 else _np.nan
    def team_stats(team, prior, date):
        g = prior[(prior['home_team']==team)|(prior['away_team']==team)].copy()
        if len(g)<3: return [_np.nan]*5
        days_ago = [(date - d).days for d in g['date']]
        w = [_math.exp(-decay*d) for d in days_ago]
        scored, conceded, xg_v, xga_v, wins = [], [], [], [], []
        for (_, r), wi in zip(g.iterrows(), w):
            is_home = r['home_team']==team
            scored.append(r['home_goals'] if is_home else r['away_goals'])
            conceded.append(r['away_goals'] if is_home else r['home_goals'])
            wins.append(1.0 if (is_home and r['home_goals']>r['away_goals'])
                        or (not is_home and r['away_goals']>r['home_goals']) else 0.0)
            if 'home_xg' in r: xg_v.append(r['home_xg'] if is_home else r['away_xg'])
            if 'away_xg' in r: xga_v.append(r['away_xg'] if is_home else r['home_xg'])
        return [weighted_mean(scored,w), weighted_mean(conceded,w),
                weighted_mean(xg_v,w) if xg_v else _np.nan,
                weighted_mean(xga_v,w) if xga_v else _np.nan,
                weighted_mean(wins,w)]
    for i in range(len(df)):
        prior = df.iloc[:i]
        row = df.iloc[i]
        hs = team_stats(row['home_team'], prior, row['date'])
        as_ = team_stats(row['away_team'], prior, row['date'])
        for j, k in enumerate(['home_td_goals_scored','home_td_goals_conceded',
                                'home_td_xg','home_td_xga','home_td_win_rate']):
            cols[k].append(hs[j])
        for j, k in enumerate(['away_td_goals_scored','away_td_goals_conceded',
                                'away_td_xg','away_td_xga','away_td_win_rate']):
            cols[k].append(as_[j])
    for k, v in cols.items():
        df[k] = v
    return df


def compute_h2h_features(df, window=5):
    import pandas as _pd, numpy as _np
    df = df.copy()
    df['date'] = _pd.to_datetime(df['date'])
    h2h_cols = {k:[] for k in ['h2h_home_wins','h2h_away_wins','h2h_draws',
                                'h2h_avg_goals','h2h_btts_rate','h2h_n']}
    for i in range(len(df)):
        prior = df.iloc[:i]
        home, away = df.iloc[i]['home_team'], df.iloc[i]['away_team']
        h2h = prior[((prior['home_team']==home)&(prior['away_team']==away))|
                    ((prior['home_team']==away)&(prior['away_team']==home))].tail(window)
        n = len(h2h)
        if n == 0:
            for k in h2h_cols: h2h_cols[k].append(0 if k=='h2h_n' else _np.nan)
            continue
        hw = aw = dr = goals = btts = 0
        for _, r in h2h.iterrows():
            hg, ag = r['home_goals'], r['away_goals']
            is_home_perspective = r['home_team']==home
            if hg > ag: hw += (1 if is_home_perspective else 0); aw += (0 if is_home_perspective else 1)
            elif ag > hg: aw += (1 if is_home_perspective else 0); hw += (0 if is_home_perspective else 1)
            else: dr += 1
            goals += hg + ag
            btts += int(hg>=1 and ag>=1)
        h2h_cols['h2h_home_wins'].append(hw/n)
        h2h_cols['h2h_away_wins'].append(aw/n)
        h2h_cols['h2h_draws'].append(dr/n)
        h2h_cols['h2h_avg_goals'].append(goals/n)
        h2h_cols['h2h_btts_rate'].append(btts/n)
        h2h_cols['h2h_n'].append(n)
    for k, v in h2h_cols.items():
        df[k] = v
    return df


def compute_game_state_features(df, window=10):
    import pandas as _pd, numpy as _np
    df = df.copy()
    df['date'] = _pd.to_datetime(df['date'])
    out_cols = {k:[] for k in [
        'home_lead_rate','home_comeback_rate','home_clean_sheet_rate','home_failed_to_score_rate',
        'away_lead_rate','away_comeback_rate','away_clean_sheet_rate','away_failed_to_score_rate']}
    def team_gs(team, prior):
        g = prior[(prior['home_team']==team)|(prior['away_team']==team)].tail(window)
        if len(g)<3: return [_np.nan]*4
        lead=comeback=cs=fts=0
        for _, r in g.iterrows():
            ih = r['home_team']==team
            scored = r['home_goals'] if ih else r['away_goals']
            conceded = r['away_goals'] if ih else r['home_goals']
            if scored > conceded: lead+=1
            if conceded>=1 and scored>conceded: comeback+=1
            if conceded==0: cs+=1
            if scored==0: fts+=1
        n=len(g)
        return [lead/n, comeback/n, cs/n, fts/n]
    for i in range(len(df)):
        prior = df.iloc[:i]
        row = df.iloc[i]
        hs = team_gs(row['home_team'], prior)
        as_ = team_gs(row['away_team'], prior)
        for j,k in enumerate(['home_lead_rate','home_comeback_rate',
                               'home_clean_sheet_rate','home_failed_to_score_rate']):
            out_cols[k].append(hs[j])
        for j,k in enumerate(['away_lead_rate','away_comeback_rate',
                               'away_clean_sheet_rate','away_failed_to_score_rate']):
            out_cols[k].append(as_[j])
    for k,v in out_cols.items():
        df[k] = v
    return df


def build_extended_features(df,
                             include_elo=True,
                             include_h2h=True,
                             include_time_decay=True,
                             include_adj_xg=True,
                             include_game_state=True):
    import pandas as _pd
    df = df.copy()
    existing = set(df.columns)
    if include_adj_xg:
        df = compute_opponent_adjusted_xg(df)
    if include_time_decay:
        df = compute_time_decay_features(df)
    if include_h2h:
        df = compute_h2h_features(df)
    if include_game_state:
        df = compute_game_state_features(df)
    if include_elo:
        try:
            from football_prediction_v19.elo import EloRatingSystem
            elo = EloRatingSystem()
            df = elo.get_ratings_before_match(df)
        except Exception:
            pass
    # Never overwrite existing columns:
    for col in existing:
        if col in df.columns:
            pass  # already preserved by copy
    return df
