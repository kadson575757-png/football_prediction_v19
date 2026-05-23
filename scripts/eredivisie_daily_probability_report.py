# -*- coding: utf-8 -*-
"""Eredivisie Daily Probability Report.

Same style as the MLS and Serie A daily probability reports.
Uses the Eredivisie-specific model and N1 historical match data.

Usage:
    python scripts/eredivisie_daily_probability_report.py
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
from football_prediction_v19.diagnostics import build_control_chaos_profile, build_recommended_market, apply_league_market_profile
from football_prediction_v19.team_names import normalize_team_name

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

FIXTURE_FILE  = ROOT / "data" / "upcoming_eredivisie_fixtures.csv"
HISTORY_FILE  = ROOT / "data" / "processed" / "eredivisie_clean.csv"
MODEL_FILE    = ROOT / "outputs" / "model_comparison_eredivisie" / "best_model.joblib"
REPORT_DATE   = "2026-05-17"

# Local name patches: normalize_team_name output -> history canonical name
# History stores "For Sittard"; fixtures say "Fortuna Sittard"
NAME_PATCH: dict[str, str] = {
    "Fortuna Sittard": "For Sittard",
}

# ---------------------------------------------------------------------------
# Helpers  (same as MLS report)
# ---------------------------------------------------------------------------

def patch_name(name: str) -> str:
    """Apply local name patches after normalize_team_name."""
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


def control_chaos(p_h: float, p_d: float, p_a: float,
                  h_form: dict, a_form: dict) -> tuple[float, float]:
    p_max   = max(p_h, p_d, p_a)
    control = round(max(0, min(100, (p_max - 0.33) / (1.0 - 0.33) * 100)), 1)
    draw_wt = p_d * 100
    o25_h   = h_form.get("over25_rate") or 0.5
    o25_a   = a_form.get("over25_rate") or 0.5
    form_var = abs(o25_h - o25_a) * 100
    chaos   = round(max(0, min(100, draw_wt * 0.6 + form_var * 0.4)), 1)
    return control, chaos


# ---------------------------------------------------------------------------
# Form computation
# ---------------------------------------------------------------------------

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
        h["gf"] = h["home_goals"];  h["ga"] = h["away_goals"]
        a = past[away_mask].copy()
        a["gf"] = a["away_goals"];  a["ga"] = a["home_goals"]
        rows = pd.concat([h[["date","gf","ga"]], a[["date","gf","ga"]]], ignore_index=True)

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
        "btts_rate":   round(btts,   3),
    }


# ---------------------------------------------------------------------------
# Load resources
# ---------------------------------------------------------------------------

print(f"Loading Eredivisie history: {HISTORY_FILE}")
history = pd.read_csv(HISTORY_FILE, parse_dates=["date"])
history["home_team"] = history["home_team"].apply(normalize_team_name)
history["away_team"] = history["away_team"].apply(normalize_team_name)
# "For Sittard" passes through normalize unchanged — keep as-is in history
print(f"  {len(history)} matches  |  "
      f"{history['date'].min().date()} to {history['date'].max().date()}")

print(f"Loading model: {MODEL_FILE}")
bundle        = joblib.load(MODEL_FILE)
model         = bundle["model"]
feature_cols  = bundle["feature_cols"]
print(f"  Classes: {model.classes_}  |  accuracy={bundle['metrics']['accuracy']:.3f}")

print(f"Loading fixtures: {FIXTURE_FILE}")
fixtures = pd.read_csv(FIXTURE_FILE, parse_dates=["date"])
# Normalize fixture team names, then apply local patches
fixtures["home_team"] = fixtures["home_team"].apply(normalize_team_name).apply(patch_name)
fixtures["away_team"] = fixtures["away_team"].apply(normalize_team_name).apply(patch_name)
fixtures = fixtures[fixtures["date"].dt.date == pd.Timestamp(REPORT_DATE).date()].reset_index(drop=True)
print(f"  {len(fixtures)} fixtures on {REPORT_DATE}")

SEP  = "=" * 72
SEP2 = "-" * 72

print()
print(SEP)
print(f"  EREDIVISIE DAILY PROBABILITY REPORT  --  {REPORT_DATE}")
print(f"  History: {len(history)} Eredivisie matches (2021-2025, 4 seasons)")
print(f"  Model  : Eredivisie-specific (accuracy={bundle['metrics']['accuracy']:.3f})")
print(SEP)
print()
print("  This report shows probability estimates only.")
print("  No value, ROI, profitability, or paper-test claims are made.")
print()

# ---------------------------------------------------------------------------
# Pre-match report
# ---------------------------------------------------------------------------

results = []

for _, fix in fixtures.iterrows():
    home      = fix["home_team"]
    away      = fix["away_team"]
    game_date = pd.to_datetime(fix["date"])
    game_time = str(fix.get("time", ""))
    venue     = str(fix.get("venue", "Unknown"))
    referee   = str(fix.get("referee", "Unknown"))
    odds_h    = float(fix["odds_home"])
    odds_d    = float(fix["odds_draw"])
    odds_a    = float(fix["odds_away"])

    # Market implied (overround-adjusted)
    raw_h, raw_d, raw_a = 1/odds_h, 1/odds_d, 1/odds_a
    ov = raw_h + raw_d + raw_a
    mkt_h, mkt_d, mkt_a = raw_h/ov, raw_d/ov, raw_a/ov

    # ---- Form features ----
    h_all  = team_form(history, home, game_date)
    a_all  = team_form(history, away, game_date)
    h_home = team_form(history, home, game_date, venue_side="home")
    a_away = team_form(history, away, game_date, venue_side="away")

    data_ok = h_all["n"] >= 3 and a_all["n"] >= 3

    over25_p = avg_rate(h_all.get("over25_rate"), a_all.get("over25_rate"))
    btts_p   = avg_rate(h_all.get("btts_rate"),   a_all.get("btts_rate"))

    # Pattern flags
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

    # ---- Model prediction ----
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
    except Exception as e:
        pass  # fall back to market

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

    ctrl, chaos = control_chaos(p_h, p_d, p_a, h_all, a_all)

    mkt_map   = {"Home": mkt_h, "Draw": mkt_d, "Away": mkt_a}
    mkt_best  = max(mkt_map, key=mkt_map.get)
    diverge   = (mkt_best != best_1x2) or (abs(best_prob - mkt_map[mkt_best]) > 0.15)
    no_conf   = (conf in ("LOW", "NO-CONFIDENCE")) or (p_d > 0.30) or (ctrl < 25)

    # ---- Print block ----
    print(SEP)
    print(f"  Eredivisie {game_time}  |  {home} vs {away}")
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
                  f"pts={f_all['pts']}  "
                  f"GF={f_all['gf']:.0f}  GA={f_all['ga']:.0f}  "
                  f"Over25={f_all['over25_rate']*100:.0f}%  "
                  f"BTTS={f_all['btts_rate']*100:.0f}%")
            if f_ven["n"] >= 2:
                print(f"    {' '*30} [{v_label}]  "
                      f"W{f_ven['wins']} D{f_ven['draws']} L{f_ven['losses']}  "
                      f"pts={f_ven['pts']}  "
                      f"GF={f_ven['gf']:.0f}  GA={f_ven['ga']:.0f}  "
                      f"Over25={f_ven['over25_rate']*100:.0f}%")
            else:
                print(f"    {' '*30} [{v_label}]  n={f_ven['n']} (insufficient venue data)")
        else:
            n_warn = f_all["n"]
            print(f"    {team_name[:30]:<30}  ** insufficient history (n={n_warn}) **")

    flags = []
    if home_gf_high:    flags.append("home_gf_high")
    if form_mismatch_H: flags.append("form_mismatch_H")
    if both_over_flag:  flags.append("both_over")
    if both_btts_flag:  flags.append("both_btts")
    print(f"\n  Pattern flags: {', '.join(flags) if flags else 'none'}")

    ctrl_bar  = "#" * int(ctrl  / 10)
    chaos_bar = "#" * int(chaos / 10)
    print(f"\n  Control Score : {ctrl:5.1f} / 100  [{ctrl_bar:<10}]")
    print(f"  Chaos Score   : {chaos:5.1f} / 100  [{chaos_bar:<10}]")
    diagnostic_profile = build_control_chaos_profile({
        "odds_home": odds_h,
        "odds_draw": odds_d,
        "odds_away": odds_a,
        "model_home_prob": p_h,
        "model_draw_prob": p_d,
        "model_away_prob": p_a,
        "control_score": ctrl / 10,
        "chaos_score": chaos / 10,
        "likely_1x2": best_1x2,
        "both_over": both_over_flag,
        "both_btts": both_btts_flag,
        "home_gf_high": home_gf_high,
        "form_mismatch_H": form_mismatch_H,
    })
    print("\n  CONTROL/CHAOS PROFILE  [diagnostic only]")
    print(f"    probability_profile : {diagnostic_profile['probability_profile']}")
    print(f"    direction_read      : {diagnostic_profile['direction_read']}")
    print(f"    goals_read          : {diagnostic_profile['goals_read']}")
    print(f"    risk_warning        : {diagnostic_profile['risk_warning']}")
    print(f"    score_family        : {diagnostic_profile['score_family']}")
    favorite_strength = diagnostic_profile["home_favorite_strength"] if diagnostic_profile["favorite_side"] == "HOME_FAVORITE" else diagnostic_profile["away_favorite_strength"]
    recommended_market = build_recommended_market({
        "league": "Eredivisie",
        "likely_1x2": best_1x2,
        "model_home_prob": p_h,
        "model_draw_prob": p_d,
        "model_away_prob": p_a,
        "odds_home": odds_h,
        "odds_draw": odds_d,
        "odds_away": odds_a,
        "control_score_10": ctrl / 10,
        "chaos_score_10": chaos / 10,
        "confidence": conf,
        "favorite_side": diagnostic_profile["favorite_side"],
        "favorite_strength": favorite_strength,
        "probability_profile": diagnostic_profile["probability_profile"],
        "goals": gp,
        "over25_signal": over25_signal(over25_p),
        "btts_signal": btts_signal(btts_p),
        "data_warning": not data_ok,
        "both_over": both_over_flag,
        "both_btts": both_btts_flag,
        "score_family": diagnostic_profile["score_family"],
    })
    recommended_market = apply_league_market_profile(recommended_market, "Eredivisie")
    print("\n  RECOMMENDED MARKET TYPE  [diagnostic only]")
    print(f"    type       : {recommended_market['recommended_market_type']}")
    print(f"    read       : {recommended_market['recommended_market_read']}")
    print(f"    strength   : {recommended_market['recommendation_strength']}")
    print(f"    risk_note  : {recommended_market['risk_note']}")
    print("\n  LEAGUE PROFILE  [Eredivisie / diagnostic only]")
    print(f"    profile    : {recommended_market['league_profile']}")
    print(f"    adj.strength: {recommended_market['league_adjusted_strength']}")
    print(f"    preferred  : {recommended_market['league_preferred_subtype']}")
    print(f"    suppressed : {recommended_market['league_suppressed_subtype']}")
    if recommended_market['league_warning_flags']:
        print(f"    WARNING    : {recommended_market['league_warning_flags']}")

    if not data_ok:
        print(f"\n  ** DATA WARNING: Insufficient history for one or both teams. "
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
        "over25_p": over25_p, "btts_p": btts_p,
        "goals_pic": gp,
        "h_all": h_all, "a_all": a_all,
        "home_gf_high": home_gf_high,
        "form_mismatch_H": form_mismatch_H,
        "both_over": both_over_flag,
        "both_btts": both_btts_flag,
        "ctrl": ctrl, "chaos": chaos,
        "data_ok": data_ok, "no_conf": no_conf,
        "diverge": diverge,
        "odds_h": odds_h, "odds_d": odds_d, "odds_a": odds_a,
        "recommended_market": recommended_market,
    })

# ---------------------------------------------------------------------------
# Summary table
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
    rec = r["recommended_market"]
    print(f"  {game:<38} {r['best_1x2']:>5}  {r['best_prob']*100:4.0f}%  "
          f"{r['conf']:>14}  {rec['recommended_market_type']:<13} {rec['recommendation_strength']:<8} {r['goals_pic']}{nc}")

print()
print(SEP)
print("  RECOMMENDED MARKET TYPE SUMMARY")
print(SEP)
print(f"  {'Match':<38} {'Recommended Type':<16} {'Read':<34} {'Strength':<8} {'Control':>7} {'Chaos':>6} {'Confidence':>13}  Risk Note")
print(SEP2)
for r in results:
    game = f"{r['home'][:17]} vs {r['away'][:17]}"
    rec = r["recommended_market"]
    print(f"  {game:<38} {rec['recommended_market_type']:<16} {rec['recommended_market_read']:<34} {rec['recommendation_strength']:<8} {r['ctrl']/10:7.1f} {r['chaos']/10:6.1f} {r['conf']:>13}  {rec['risk_note']}")

# ---------------------------------------------------------------------------
# Final analytical report
# ---------------------------------------------------------------------------

print()
print(SEP)
print("  FINAL ANALYTICAL REPORT")
print(SEP)

# Cleanest call = highest best_prob among data_ok games
data_ok_games = [r for r in results if r["data_ok"]]
if data_ok_games:
    cleanest = max(data_ok_games, key=lambda r: r["best_prob"])
    print(f"\n  CLEANEST PROBABILITY CALL:")
    print(f"    {cleanest['home']} vs {cleanest['away']}")
    print(f"    -> {cleanest['best_1x2']} ({cleanest['best_prob']*100:.1f}%)  [{cleanest['conf']}]")
    print(f"       Market: {cleanest['mkt_h']*100:.0f}% / {cleanest['mkt_d']*100:.0f}% / {cleanest['mkt_a']*100:.0f}%")

# Most unclear / dangerous
most_unclear = max(results, key=lambda r: r["chaos"])
print(f"\n  MOST DANGEROUS / UNCLEAR:")
print(f"    {most_unclear['home']} vs {most_unclear['away']}")
print(f"    Chaos={most_unclear['chaos']:.0f}/100  Control={most_unclear['ctrl']:.0f}/100")
print(f"    Draw p={most_unclear['p_d']*100:.0f}%  Goals: {most_unclear['goals_pic']}")

# Over 2.5 ranking
print(f"\n  OVER 2.5 RANKING (by form signal, highest first):")
over25_ranked = sorted([r for r in results if r["over25_p"] is not None],
                       key=lambda r: r["over25_p"], reverse=True)
for r in over25_ranked:
    flag = " <- OVER likely" if r["over25_p"] >= 0.62 else (" <- UNDER likely" if r["over25_p"] <= 0.42 else "")
    print(f"    {r['home'][:17]} vs {r['away'][:17]:<17}  {r['over25_p']*100:.0f}%{flag}")

# BTTS ranking
print(f"\n  BTTS RANKING (by form signal, highest first):")
btts_ranked = sorted([r for r in results if r["btts_p"] is not None],
                     key=lambda r: r["btts_p"], reverse=True)
for r in btts_ranked:
    flag = " <- BTTS likely" if r["btts_p"] >= 0.60 else (" <- NOT-BTTS likely" if r["btts_p"] <= 0.38 else "")
    print(f"    {r['home'][:17]} vs {r['away'][:17]:<17}  {r['btts_p']*100:.0f}%{flag}")

# Safest favourite
high_conf = [r for r in results if r["conf"] in ("HIGH", "MEDIUM") and r["data_ok"]]
if high_conf:
    safest = max(high_conf, key=lambda r: r["best_prob"])
    print(f"\n  SAFEST FAVOURITE BY PROBABILITY:")
    print(f"    {safest['home']} vs {safest['away']}")
    print(f"    -> {safest['best_1x2']} {safest['best_prob']*100:.1f}%  [{safest['conf']}]"
          f"  market implied: {safest['mkt_h']*100:.0f}%/{safest['mkt_d']*100:.0f}%/{safest['mkt_a']*100:.0f}%")
else:
    print(f"\n  SAFEST FAVOURITE: No HIGH or MEDIUM confidence games with sufficient data.")

# Dangerous away teams
print(f"\n  DANGEROUS AWAY TEAMS (model away prob > 35% or model > market by 5pp+):")
away_threats = []
for r in results:
    if r["model_a"] is not None and not np.isnan(r["model_a"]):
        model_a_pct = r["model_a"] * 100
        mkt_a_pct   = r["mkt_a"]   * 100
        excess      = model_a_pct - mkt_a_pct
        if model_a_pct > 35 or excess > 5:
            away_threats.append((r, model_a_pct, mkt_a_pct, excess))
away_threats.sort(key=lambda x: x[1], reverse=True)
if away_threats:
    for r, ma, mka, exc in away_threats:
        print(f"    {r['away']:<25} @ {r['home']:<25}  "
              f"model_away={ma:.0f}%  mkt_away={mka:.0f}%  "
              f"excess={exc:+.0f}pp")
else:
    print("    None detected above threshold.")

# No-confidence summary
nc_games = [r for r in results if r["no_conf"]]
print(f"\n  NO-CONFIDENCE GAMES ({len(nc_games)}/{len(results)}):")
for r in nc_games:
    print(f"    {r['home']} vs {r['away']}  "
          f"[draw={r['p_d']*100:.0f}%  ctrl={r['ctrl']:.0f}/100  conf={r['conf']}]")

print()
print(SEP)
print("  NOTE: Probabilities are model/market estimates. No betting claims.")
print("  Over2.5 / BTTS are rolling form rates (last 5 games). No edge claims.")
print("  Model: Eredivisie-specific, accuracy=50.2% on held-out 2023-24 OOS data.")
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
        "date":                      REPORT_DATE,
        "league":                    "Eredivisie",
        "home_team":                 r["home"],
        "away_team":                 r["away"],
        "likely_1x2":               r["best_1x2"],
        "confidence":                r["conf"],
        "model_home_prob":           round(r["p_h"], 4),
        "model_draw_prob":           round(r["p_d"], 4),
        "model_away_prob":           round(r["p_a"], 4),
        "odds_home":                 r["odds_h"],
        "odds_draw":                 r["odds_d"],
        "odds_away":                 r["odds_a"],
        "control_10":                round(r["ctrl"] / 10, 2),
        "chaos_10":                  round(r["chaos"] / 10, 2),
        "over25_p":                  r["over25_p"],
        "btts_p":                    r["btts_p"],
        "data_ok":                   r["data_ok"],
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
    })
import pandas as _pd
_df = _pd.DataFrame(_csv_rows)
_csv_path = _out_dir / f"eredivisie_{REPORT_DATE}_daily_report.csv"
_df.to_csv(_csv_path, index=False)
print(f"  [CSV saved] {_csv_path}")
