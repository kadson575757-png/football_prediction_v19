# -*- coding: utf-8 -*-
"""Brasileiro Série A Daily Probability Report.

Same style as the existing daily probability reports (Eredivisie, La Liga, etc.).
Uses BRA historical match data and falls back to the top-5 shared model when no
Brazil-specific model exists.

Usage:
    python scripts/brazil_daily_probability_report.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.features import build_fixture_features
from football_prediction_v19.diagnostics import (
    build_control_chaos_profile,
    build_recommended_market,
    apply_league_market_profile,
    build_market_tier,
)
from football_prediction_v19.team_names import normalize_team_name
from football_prediction_v19.reports.watchlist import append_watchlist_to_report
from _watchlist import print_priority_watchlist

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

LEAGUE_NAME   = "Brasileiro Serie A"
LEAGUE_TAG    = "brazil"
REPORT_DATE   = pd.Timestamp.today().strftime("%Y-%m-%d")

FIXTURE_FILE  = ROOT / "data" / "upcoming_brazil_fixtures.csv"

# Primary: Brazil-specific model; fallback: shared top-5 model
_MODEL_BRAZIL   = ROOT / "outputs" / "model_comparison_brazil"  / "best_model.joblib"
_MODEL_SHARED   = ROOT / "outputs" / "model_comparison_top5"    / "best_model.joblib"
_MODEL_FALLBACK = ROOT / "outputs" / "model_comparison"         / "best_model.joblib"

# Historical data: prefer processed file, fall back to raw
_HIST_PROCESSED = ROOT / "data" / "processed" / "brazil_clean.csv"
_HIST_RAW_2025  = ROOT / "data" / "raw" / "football_data_BRA_2025.csv"
_HIST_RAW_2024  = ROOT / "data" / "raw" / "football_data_BRA_2024.csv"

# Local name patches (normalize_team_name output → history canonical name)
NAME_PATCH: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def patch_name(name: str) -> str:
    return NAME_PATCH.get(name, name)


def confidence_label(p_max: float, data_ok: bool) -> str:
    if not data_ok:
        return "NO-CONFIDENCE"
    if p_max >= 0.65:
        return "HIGH"
    if p_max >= 0.50:
        return "MEDIUM"
    return "LOW"


def over25_signal(p: float | None) -> str:
    if p is None:
        return "n/a"
    if p >= 0.62:
        return f"OVER  likely ({p*100:.0f}%)"
    if p <= 0.42:
        return f"UNDER likely ({(1-p)*100:.0f}% under)"
    return f"unclear ({p*100:.0f}% over)"


def btts_signal(p: float | None) -> str:
    if p is None:
        return "n/a"
    if p >= 0.60:
        return f"BTTS YES likely ({p*100:.0f}%)"
    if p <= 0.38:
        return f"BTTS NO  likely ({(1-p)*100:.0f}% no-btts)"
    return f"unclear ({p*100:.0f}% btts)"


def goals_picture(over25_p: float | None, btts_p: float | None) -> str:
    parts = []
    if over25_p is not None:
        if over25_p >= 0.62:
            parts.append(f"Over2.5 ({over25_p*100:.0f}%)")
        elif over25_p <= 0.42:
            parts.append(f"Under2.5 ({(1-over25_p)*100:.0f}%)")
    if btts_p is not None:
        if btts_p >= 0.58:
            parts.append(f"BTTS ({btts_p*100:.0f}%)")
        elif btts_p <= 0.38:
            parts.append(f"NOT-BTTS ({(1-btts_p)*100:.0f}%)")
    return " + ".join(parts) if parts else "unclear"


def avg_rate(a: float | None, b: float | None) -> float | None:
    vals = [v for v in [a, b] if v is not None]
    return round(float(np.mean(vals)), 3) if vals else None


def team_form(history: pd.DataFrame, team: str, before_date: pd.Timestamp,
              venue_side: str | None = None, n: int = 5) -> dict:
    past = history[history["date"] < before_date].copy()
    home_mask = past["home_team"] == team
    away_mask = past["away_team"] == team

    if venue_side == "home":
        rows = past[home_mask].copy()
        rows["gf"] = rows["home_goals"]
        rows["ga"] = rows["away_goals"]
    elif venue_side == "away":
        rows = past[away_mask].copy()
        rows["gf"] = rows["away_goals"]
        rows["ga"] = rows["home_goals"]
    else:
        h = past[home_mask].copy()
        h["gf"] = h["home_goals"]; h["ga"] = h["away_goals"]
        a = past[away_mask].copy()
        a["gf"] = a["away_goals"]; a["ga"] = a["home_goals"]
        rows = pd.concat([h[["date", "gf", "ga"]], a[["date", "gf", "ga"]]], ignore_index=True)

    rows = rows.sort_values("date").tail(n)
    n_games = len(rows)
    if n_games == 0:
        return {"n": 0, "wins": 0, "draws": 0, "losses": 0, "pts": None,
                "gf": None, "ga": None, "over25_rate": None, "btts_rate": None}

    gf = rows["gf"].fillna(0)
    ga = rows["ga"].fillna(0)
    wins   = int((gf >  ga).sum())
    draws  = int((gf == ga).sum())
    losses = int((gf <  ga).sum())
    pts    = wins * 3 + draws
    over25 = float(((gf + ga) > 2.5).mean())
    btts   = float(((gf > 0) & (ga > 0)).mean())
    return {
        "n": n_games,
        "wins": wins, "draws": draws, "losses": losses,
        "pts": pts,
        "gf": float(gf.sum()),
        "ga": float(ga.sum()),
        "over25_rate": round(over25, 3),
        "btts_rate":   round(btts, 3),
    }


# ---------------------------------------------------------------------------
# Load resources
# ---------------------------------------------------------------------------

if _HIST_PROCESSED.exists():
    print(f"Loading Brazil history (processed): {_HIST_PROCESSED}")
    history = pd.read_csv(_HIST_PROCESSED, parse_dates=["date"])
else:
    raw_parts = []
    for p in [_HIST_RAW_2024, _HIST_RAW_2025]:
        if p.exists():
            raw_parts.append(pd.read_csv(p))
    if not raw_parts:
        print("[WARN] No Brazil historical data found. "
              "Place football_data_BRA_2024.csv / football_data_BRA_2025.csv in data/raw/")
        sys.exit(1)
    raw = pd.concat(raw_parts, ignore_index=True)
    col_map = {
        "HomeTeam": "home_team", "AwayTeam": "away_team",
        "FTHG": "home_goals",   "FTAG": "away_goals",
        "FTR":  "result",       "Date": "date",
    }
    raw = raw.rename(columns={k: v for k, v in col_map.items() if k in raw.columns})
    raw["date"] = pd.to_datetime(raw["date"], dayfirst=True, errors="coerce")
    raw = raw.dropna(subset=["date", "home_team", "away_team", "home_goals", "away_goals"])
    history = raw
    print(f"Loading Brazil history (raw BRA files): {len(history)} matches")

history["home_team"] = history["home_team"].apply(normalize_team_name)
history["away_team"] = history["away_team"].apply(normalize_team_name)
print(f"  {len(history)} matches  |  "
      f"{history['date'].min().date()} to {history['date'].max().date()}")

for model_path in [_MODEL_BRAZIL, _MODEL_SHARED, _MODEL_FALLBACK]:
    if model_path.exists():
        MODEL_FILE = model_path
        break
else:
    print("[ERROR] No model file found. Run model comparison first.")
    sys.exit(1)

print(f"Loading model: {MODEL_FILE}")
bundle       = joblib.load(MODEL_FILE)
model        = bundle["model"]
feature_cols = bundle["feature_cols"]
print(f"  Classes: {model.classes_}  |  accuracy={bundle['metrics']['accuracy']:.3f}")

print(f"Loading fixtures: {FIXTURE_FILE}")
if not FIXTURE_FILE.exists():
    print(f"[WARN] Fixture file not found: {FIXTURE_FILE}")
    fixtures = pd.DataFrame()
else:
    fixtures = pd.read_csv(FIXTURE_FILE, parse_dates=["date"])
    fixtures["home_team"] = fixtures["home_team"].apply(normalize_team_name).apply(patch_name)
    fixtures["away_team"] = fixtures["away_team"].apply(normalize_team_name).apply(patch_name)
    fixtures = fixtures[fixtures["date"].dt.date == pd.Timestamp(REPORT_DATE).date()].reset_index(drop=True)
print(f"  {len(fixtures)} fixtures on {REPORT_DATE}")

SEP  = "=" * 72
SEP2 = "-" * 72

print()
print(SEP)
print(f"  BRASILEIRO SÉRIE A DAILY PROBABILITY REPORT  --  {REPORT_DATE}")
print(f"  History: {len(history)} Brasileiro Serie A matches")
print(f"  Model  : {MODEL_FILE.name}  (accuracy={bundle['metrics']['accuracy']:.3f})")
print(SEP)
print()
print("  This report shows probability estimates only.")
print("  No value, ROI, profitability, or paper-test claims are made.")
print()

if fixtures.empty:
    print("  [INFO] No fixtures for today. Nothing to report.")
    sys.exit(0)

# ---------------------------------------------------------------------------
# Pre-match report loop
# ---------------------------------------------------------------------------

results = []

for _, fix in fixtures.iterrows():
    home      = fix["home_team"]
    away      = fix["away_team"]
    game_date = pd.to_datetime(fix["date"])
    game_time = str(fix.get("time", ""))
    venue     = str(fix.get("venue", "Unknown"))
    referee   = str(fix.get("referee", "Unknown"))
    odds_h    = float(fix.get("odds_home", 2.0))
    odds_d    = float(fix.get("odds_draw", 3.3))
    odds_a    = float(fix.get("odds_away", 3.5))

    raw_h, raw_d, raw_a = 1/odds_h, 1/odds_d, 1/odds_a
    ov = raw_h + raw_d + raw_a
    mkt_h, mkt_d, mkt_a = raw_h/ov, raw_d/ov, raw_a/ov

    h_all  = team_form(history, home, game_date)
    a_all  = team_form(history, away, game_date)
    h_home = team_form(history, home, game_date, venue_side="home")
    a_away = team_form(history, away, game_date, venue_side="away")

    data_ok  = h_all["n"] >= 3 and a_all["n"] >= 3
    over25_p = avg_rate(h_all.get("over25_rate"), a_all.get("over25_rate"))
    btts_p   = avg_rate(h_all.get("btts_rate"),   a_all.get("btts_rate"))

    home_gf_high    = (h_all["gf"] is not None and h_all["gf"] >= 10)
    form_mismatch_H = (h_all["pts"] is not None and a_all["pts"] is not None
                       and h_all["pts"] >= 10 and a_all["pts"] <= 5)
    both_over_flag  = (h_all.get("over25_rate") is not None
                       and a_all.get("over25_rate") is not None
                       and h_all["over25_rate"] >= 0.60
                       and a_all["over25_rate"] >= 0.60)
    both_btts_flag  = (h_all.get("btts_rate") is not None
                       and a_all.get("btts_rate") is not None
                       and h_all["btts_rate"] >= 0.60
                       and a_all["btts_rate"] >= 0.60)

    model_h = model_d = model_a = None
    try:
        feat_df = build_fixture_features(
            history_df=history,
            home_team=home,
            away_team=away,
            match_date=game_date,
            venue=venue,
            referee=referee,
            odds_home=odds_h,
            odds_draw=odds_d,
            odds_away=odds_a,
        )
        for col in feature_cols:
            if col not in feat_df.columns:
                feat_df[col] = np.nan
        X = feat_df[feature_cols]
        proba    = model.predict_proba(X)[0]
        prob_map = dict(zip(model.classes_, proba))
        model_h  = prob_map.get("H", np.nan)
        model_d  = prob_map.get("D", np.nan)
        model_a  = prob_map.get("A", np.nan)
    except Exception:
        pass

    if model_h is not None and not np.isnan(model_h):
        p_h, p_d, p_a = model_h, model_d, model_a
        prob_src = "model"
    else:
        p_h, p_d, p_a = mkt_h, mkt_d, mkt_a
        prob_src = "market"

    probs_map = {"Home": p_h, "Draw": p_d, "Away": p_a}
    best_1x2  = max(probs_map, key=probs_map.get)
    best_prob = probs_map[best_1x2]
    conf      = confidence_label(best_prob, data_ok)

    p_max   = max(p_h, p_d, p_a)
    ctrl    = round(max(0, min(100, (p_max - 0.33) / (1.0 - 0.33) * 100)), 1)
    draw_wt = p_d * 100
    o25_h   = h_all.get("over25_rate") or 0.5
    o25_a   = a_all.get("over25_rate") or 0.5
    chaos   = round(max(0, min(100, draw_wt * 0.6 + abs(o25_h - o25_a) * 100 * 0.4)), 1)

    mkt_map  = {"Home": mkt_h, "Draw": mkt_d, "Away": mkt_a}
    mkt_best = max(mkt_map, key=mkt_map.get)
    diverge  = (mkt_best != best_1x2) or (abs(best_prob - mkt_map[mkt_best]) > 0.15)
    no_conf  = (conf in ("LOW", "NO-CONFIDENCE")) or (p_d > 0.30) or (ctrl < 25)

    print(SEP)
    print(f"  Brasileiro Série A {game_time}  |  {home} vs {away}")
    print(SEP)
    print(f"  1X2 PROBABILITIES  [{prob_src}]")
    for label, pval in [("Home", p_h), ("Draw", p_d), ("Away", p_a)]:
        arrow = " <--" if label == best_1x2 else ""
        print(f"    {label:<4}: {pval*100:5.1f}%{arrow}")
    print(f"  Most likely result : {best_1x2} ({best_prob*100:.1f}%)")
    print(f"  Confidence         : {conf}")
    print(f"\n  Market odds (informative): H {odds_h:.2f}  D {odds_d:.2f}  A {odds_a:.2f}")
    print(f"  Market implied:            H {mkt_h*100:.1f}%  D {mkt_d*100:.1f}%  A {mkt_a*100:.1f}%")
    if model_h is not None and not np.isnan(model_h):
        print(f"  Model predicted:           H {model_h*100:.1f}%  D {model_d*100:.1f}%  A {model_a*100:.1f}%")
    if diverge:
        print(f"  ** WARNING: Model and market disagree "
              f"(model={best_1x2} {best_prob*100:.0f}%, market={mkt_best} {mkt_map[mkt_best]*100:.0f}%)")
    print(f"\n  GOALS PICTURE  [form-based, last 5 games each team]")
    print(f"    Over 2.5  : {over25_signal(over25_p)}")
    print(f"    BTTS      : {btts_signal(btts_p)}")
    gp = goals_picture(over25_p, btts_p)
    print(f"    Most likely  : {gp}")
    print(f"\n  FORM  [last 5 overall | last 5 venue-specific]")
    for team_name, f_all, f_ven, v_label in [
        (home, h_all, h_home, "home"),
        (away, a_all, a_away, "away"),
    ]:
        if f_all["n"] >= 3:
            print(f"    {team_name[:30]:<30} [all]   "
                  f"W{f_all['wins']} D{f_all['draws']} L{f_all['losses']}  "
                  f"pts={f_all['pts']}  GF={f_all['gf']:.0f}  GA={f_all['ga']:.0f}  "
                  f"Over25={f_all['over25_rate']*100:.0f}%  BTTS={f_all['btts_rate']*100:.0f}%")
            if f_ven["n"] >= 2:
                print(f"    {' '*30} [{v_label}]  "
                      f"W{f_ven['wins']} D{f_ven['draws']} L{f_ven['losses']}  "
                      f"pts={f_ven['pts']}  GF={f_ven['gf']:.0f}  GA={f_ven['ga']:.0f}  "
                      f"Over25={f_ven['over25_rate']*100:.0f}%")
            else:
                print(f"    {' '*30} [{v_label}]  n={f_ven['n']} (insufficient venue data)")
        else:
            print(f"    {team_name[:30]:<30}  ** insufficient history (n={f_all['n']}) **")

    ctrl_bar  = "#" * int(ctrl  / 10)
    chaos_bar = "#" * int(chaos / 10)
    print(f"\n  Control Score : {ctrl:5.1f} / 100  [{ctrl_bar:<10}]")
    print(f"  Chaos Score   : {chaos:5.1f} / 100  [{chaos_bar:<10}]")

    diagnostic_profile = build_control_chaos_profile({
        "odds_home": odds_h, "odds_draw": odds_d, "odds_away": odds_a,
        "model_home_prob": p_h, "model_draw_prob": p_d, "model_away_prob": p_a,
        "control_score": ctrl / 10, "chaos_score": chaos / 10,
        "likely_1x2": best_1x2,
        "both_over": both_over_flag, "both_btts": both_btts_flag,
        "home_gf_high": home_gf_high, "form_mismatch_H": form_mismatch_H,
    })
    fav_strength = (diagnostic_profile["home_favorite_strength"]
                    if diagnostic_profile["favorite_side"] == "HOME_FAVORITE"
                    else diagnostic_profile["away_favorite_strength"])

    recommended_market = build_recommended_market({
        "league": LEAGUE_NAME,
        "likely_1x2": best_1x2,
        "model_home_prob": p_h, "model_draw_prob": p_d, "model_away_prob": p_a,
        "odds_home": odds_h, "odds_draw": odds_d, "odds_away": odds_a,
        "control_score_10": ctrl / 10, "chaos_score_10": chaos / 10,
        "confidence": conf,
        "favorite_side": diagnostic_profile["favorite_side"],
        "favorite_strength": fav_strength,
        "probability_profile": diagnostic_profile["probability_profile"],
        "goals": gp,
        "over25_signal": over25_signal(over25_p),
        "btts_signal": btts_signal(btts_p),
        "data_warning": not data_ok,
        "both_over": both_over_flag, "both_btts": both_btts_flag,
        "score_family": diagnostic_profile["score_family"],
    })
    recommended_market = apply_league_market_profile(recommended_market, LEAGUE_NAME)
    recommended_market = build_market_tier(recommended_market)

    print("\n  RECOMMENDED MARKET TYPE  [diagnostic only]")
    print(f"    type       : {recommended_market['recommended_market_type']}")
    print(f"    subtype    : {recommended_market.get('recommended_market_subtype', 'NONE')}")
    print(f"    read       : {recommended_market['recommended_market_read']}")
    print(f"    strength   : {recommended_market['recommendation_strength']}")
    print(f"    risk_note  : {recommended_market['risk_note']}")
    print(f"\n  LEAGUE PROFILE  [{LEAGUE_NAME} / diagnostic only]")
    print(f"    profile    : {recommended_market['league_profile']}")
    print(f"    adj.strength: {recommended_market['league_adjusted_strength']}")
    print(f"    preferred  : {recommended_market['league_preferred_subtype']}")
    print(f"    suppressed : {recommended_market['league_suppressed_subtype']}")
    if recommended_market["league_warning_flags"]:
        print(f"    WARNING    : {recommended_market['league_warning_flags']}")
    print("\n  MARKET TIER  [diagnostic only]")
    print(f"    tier       : {recommended_market['market_tier']}")
    print(f"    score      : {recommended_market['market_tier_score']}/100")
    print(f"    reason     : {recommended_market['market_tier_reason']}")
    if recommended_market["market_tier_flags"]:
        print(f"    flags      : {recommended_market['market_tier_flags']}")

    if not data_ok:
        print(f"\n  ** DATA WARNING: Insufficient history "
              f"(home n={h_all['n']}, away n={a_all['n']})")
    if no_conf:
        print(f"\n  ** NO-CONFIDENCE **  "
              f"Draw p={p_d*100:.0f}% or control={ctrl:.0f}/100 — outcome unclear.")
    print()

    results.append({
        "home": home, "away": away,
        "p_h": p_h, "p_d": p_d, "p_a": p_a,
        "mkt_h": mkt_h, "mkt_d": mkt_d, "mkt_a": mkt_a,
        "model_h": model_h, "model_d": model_d, "model_a": model_a,
        "prob_src": prob_src,
        "best_1x2": best_1x2, "best_prob": best_prob, "conf": conf,
        "over25_p": over25_p, "btts_p": btts_p, "goals_pic": gp,
        "h_all": h_all, "a_all": a_all,
        "home_gf_high": home_gf_high, "form_mismatch_H": form_mismatch_H,
        "both_over": both_over_flag, "both_btts": both_btts_flag,
        "ctrl": ctrl, "chaos": chaos,
        "data_ok": data_ok, "no_conf": no_conf, "diverge": diverge,
        "odds_h": odds_h, "odds_d": odds_d, "odds_a": odds_a,
        "recommended_market": recommended_market,
    })

# ---------------------------------------------------------------------------
# Summary tables
# ---------------------------------------------------------------------------

print()
print(SEP)
print("  PRE-MATCH SUMMARY")
print(SEP)
print(f"  {'Game':<38} {'1X2':>5}  {'%':>5}  {'Conf':>14}  {'Type':<13} {'Strength':<8} Goals")
print(SEP2)
for r in results:
    game = f"{r['home'][:17]} vs {r['away'][:17]}"
    nc   = " *NC*" if r["no_conf"] else ""
    rec  = r["recommended_market"]
    print(f"  {game:<38} {r['best_1x2']:>5}  {r['best_prob']*100:4.0f}%  "
          f"{r['conf']:>14}  {rec['recommended_market_type']:<13} "
          f"{rec['recommendation_strength']:<8} {r['goals_pic']}{nc}")

print()
print(SEP)
print("  RECOMMENDED MARKET TYPE SUMMARY")
print(SEP)
print(f"  {'Match':<38} {'Type':<16} {'Read':<34} {'Str':<8} "
      f"{'Ctrl':>7} {'Chaos':>6} {'Conf':>13}  {'Tier'}")
print(SEP2)
for r in results:
    game = f"{r['home'][:17]} vs {r['away'][:17]}"
    rec  = r["recommended_market"]
    print(f"  {game:<38} {rec['recommended_market_type']:<16} "
          f"{rec['recommended_market_read']:<34} {rec['recommendation_strength']:<8} "
          f"{r['ctrl']/10:7.1f} {r['chaos']/10:6.1f} {r['conf']:>13}  "
          f"{rec['market_tier']}")

print()
print(SEP)
print_priority_watchlist(results, LEAGUE_NAME, sep=SEP)

print("  NOTE: Probabilities are model/market estimates. No betting claims.")
print("  Over2.5 / BTTS are rolling form rates (last 5 games). No edge claims.")
print("  Profile: brazil_volatile_control (new league — treat BTTS/Over-combo cautiously).")
print(SEP)
print()

# ---------------------------------------------------------------------------
# Save structured CSV for post-match evaluation
# ---------------------------------------------------------------------------
_out_dir = ROOT / "outputs" / "daily_reports"
_out_dir.mkdir(parents=True, exist_ok=True)
_csv_rows = []
for r in results:
    rec = r["recommended_market"]
    _csv_rows.append({
        "date":                       REPORT_DATE,
        "league":                     LEAGUE_NAME,
        "home_team":                  r["home"],
        "away_team":                  r["away"],
        "likely_1x2":                 r["best_1x2"],
        "confidence":                 r["conf"],
        "model_home_prob":            round(r["p_h"], 4),
        "model_draw_prob":            round(r["p_d"], 4),
        "model_away_prob":            round(r["p_a"], 4),
        "odds_home":                  r["odds_h"],
        "odds_draw":                  r["odds_d"],
        "odds_away":                  r["odds_a"],
        "control_10":                 round(r["ctrl"] / 10, 2),
        "chaos_10":                   round(r["chaos"] / 10, 2),
        "over25_p":                   r["over25_p"],
        "btts_p":                     r["btts_p"],
        "data_ok":                    r["data_ok"],
        "recommended_market_type":    rec["recommended_market_type"],
        "recommended_market_subtype": rec.get("recommended_market_subtype", "NONE"),
        "recommended_market_read":    rec["recommended_market_read"],
        "recommendation_strength":    rec["recommendation_strength"],
        "risk_note":                  rec["risk_note"],
        "league_profile":             rec.get("league_profile", ""),
        "league_adjusted_strength":   rec.get("league_adjusted_strength", ""),
        "league_profile_note":        rec.get("league_profile_note", ""),
        "league_warning_flags":       rec.get("league_warning_flags", ""),
        "league_preferred_subtype":   rec.get("league_preferred_subtype", ""),
        "league_suppressed_subtype":  rec.get("league_suppressed_subtype", ""),
        "market_tier":                rec.get("market_tier", ""),
        "market_tier_score":          rec.get("market_tier_score", ""),
        "market_tier_reason":         rec.get("market_tier_reason", ""),
        "market_tier_flags":          rec.get("market_tier_flags", ""),
    })
import pandas as _pd
_df = _pd.DataFrame(_csv_rows)
_csv_path = _out_dir / f"{LEAGUE_TAG}_{REPORT_DATE}_daily_report.csv"
_df.to_csv(_csv_path, index=False)
print(f"  [CSV saved] {_csv_path}")
append_watchlist_to_report(str(_csv_path), _csv_rows)
