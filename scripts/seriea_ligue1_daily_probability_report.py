# -*- coding: utf-8 -*-
"""Late Serie A + Ligue 1 Daily Probability Report.

Local diagnostic only: probability / likely-outcome report, no betting logic.
"""
from __future__ import annotations

import glob
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.diagnostics import build_control_chaos_profile, build_recommended_market, apply_league_market_profile
from football_prediction_v19.features import build_fixture_features
from football_prediction_v19.team_names import normalize_team_name

MODEL_FILE = ROOT / "outputs" / "model_comparison_top5" / "best_model.joblib"
MODEL_NOTE = "best available combined Top-5 model fallback; no league-specific Serie A/F1 model found"
REPORT_DATE = "2026-05-17"

LEAGUES = [
    {
        "name": "Late Serie A",
        "fixture_file": ROOT / "data" / "upcoming_seriea_late_fixtures.csv",
        "history_pattern": str(ROOT / "data" / "processed" / "football_data_I1_*_clean.csv"),
    },
    {
        "name": "Ligue 1",
        "fixture_file": ROOT / "data" / "upcoming_ligue1_fixtures.csv",
        "history_pattern": str(ROOT / "data" / "processed" / "football_data_F1_*_clean.csv"),
    },
]

NAME_CANDIDATES = {
    "PSG": ["Paris SG", "PSG"],
}


def confidence_label(p_max: float, data_ok: bool) -> str:
    if not data_ok:
        return "NO-CONFIDENCE"
    if p_max >= 0.65:
        return "HIGH"
    if p_max >= 0.50:
        return "MEDIUM"
    return "LOW"


def control_label(control: float) -> str:
    if control >= 7.0:
        return "HIGH"
    if control >= 5.0:
        return "MEDIUM"
    return "LOW"


def chaos_label(chaos: float) -> str:
    if chaos <= 3.0:
        return "LOW"
    if chaos <= 5.0:
        return "MEDIUM"
    return "HIGH"


def control_chaos_interpretation(control: float, chaos: float) -> str:
    if control >= 7.0 and chaos <= 3.0:
        return "cleaner probability call"
    if control >= 7.0:
        return "direction okay but volatile"
    if control >= 5.0 and chaos <= 3.5:
        return "moderate / cautious"
    if control >= 5.0:
        return "uncertain / volatile"
    if chaos <= 3.5:
        return "weak conviction"
    return "dangerous / unclear"


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


def under35_signal(over25_p: float | None) -> str:
    if over25_p is None:
        return "n/a"
    if over25_p <= 0.42:
        return "UNDER 3.5 useful lean"
    if over25_p >= 0.75:
        return "UNDER 3.5 fragile"
    return "UNDER 3.5 possible but not clean"


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


def control_chaos_10(p_h: float, p_d: float, p_a: float, h_form: dict, a_form: dict) -> tuple[float, float]:
    p_max = max(p_h, p_d, p_a)
    control_100 = max(0, min(100, (p_max - 0.33) / (1.0 - 0.33) * 100))
    draw_wt = p_d * 100
    o25_h = h_form.get("over25_rate") or 0.5
    o25_a = a_form.get("over25_rate") or 0.5
    form_var = abs(o25_h - o25_a) * 100
    chaos_100 = max(0, min(100, draw_wt * 0.6 + form_var * 0.4))
    return round(control_100 / 10, 1), round(chaos_100 / 10, 1)


def team_form(history: pd.DataFrame, team: str, before_date: pd.Timestamp, venue_side: str | None = None, n: int = 5) -> dict:
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
        h["gf"] = h["home_goals"]
        h["ga"] = h["away_goals"]
        a = past[away_mask].copy()
        a["gf"] = a["away_goals"]
        a["ga"] = a["home_goals"]
        rows = pd.concat([h[["date", "gf", "ga"]], a[["date", "gf", "ga"]]], ignore_index=True)
    rows = rows.sort_values("date").tail(n)
    if rows.empty:
        return {"n": 0, "wins": 0, "draws": 0, "losses": 0, "pts": None, "gf": None, "ga": None, "over25_rate": None, "btts_rate": None}
    gf = rows["gf"].fillna(0)
    ga = rows["ga"].fillna(0)
    wins = int((gf > ga).sum())
    draws = int((gf == ga).sum())
    losses = int((gf < ga).sum())
    return {
        "n": len(rows),
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "pts": wins * 3 + draws,
        "gf": float(gf.sum()),
        "ga": float(ga.sum()),
        "over25_rate": round(float(((gf + ga) > 2.5).mean()), 3),
        "btts_rate": round(float(((gf > 0) & (ga > 0)).mean()), 3),
    }


def resolve_team(name: str, historical_teams: set[str]) -> str:
    normalized = normalize_team_name(name)
    for candidate in NAME_CANDIDATES.get(normalized, [normalized]):
        if candidate in historical_teams:
            return candidate
    return normalized


def load_history(pattern: str) -> pd.DataFrame:
    paths = sorted(glob.glob(pattern))
    history = pd.concat([pd.read_csv(path, parse_dates=["date"]) for path in paths], ignore_index=True)
    history = history.drop_duplicates(subset=["date", "home_team", "away_team"]).sort_values("date").reset_index(drop=True)
    history["home_team"] = history["home_team"].apply(normalize_team_name)
    history["away_team"] = history["away_team"].apply(normalize_team_name)
    return history


def run_league(config: dict, bundle: dict) -> list[dict]:
    league_name = config["name"]
    history = load_history(config["history_pattern"])
    historical_teams = set(history["home_team"]) | set(history["away_team"])
    fixtures = pd.read_csv(config["fixture_file"], parse_dates=["date"])
    fixtures["home_team"] = fixtures["home_team"].apply(lambda x: resolve_team(x, historical_teams))
    fixtures["away_team"] = fixtures["away_team"].apply(lambda x: resolve_team(x, historical_teams))
    fixtures = fixtures[fixtures["date"].dt.date == pd.Timestamp(REPORT_DATE).date()].reset_index(drop=True)

    model = bundle["model"]
    feature_cols = bundle["feature_cols"]
    accuracy = bundle.get("metrics", {}).get("accuracy")

    SEP = "=" * 72
    SEP2 = "-" * 72
    print()
    print(SEP)
    print(f"  {league_name.upper()} DAILY PROBABILITY REPORT  --  {REPORT_DATE}")
    print(f"  History: {len(history)} matches  |  {history['date'].min().date()} to {history['date'].max().date()}")
    print(f"  Model  : {MODEL_NOTE}" + (f" (accuracy={accuracy:.3f})" if accuracy is not None else ""))
    print(SEP)
    print("  This report shows probability estimates only.")
    print("  Control/Chaos are confidence indicators on a 0-10 scale.")
    print("  No value, ROI, profitability, ledger, or paper-test claims are made.")
    print()

    results: list[dict] = []
    data_warnings: list[str] = []
    for _, fix in fixtures.iterrows():
        home = fix["home_team"]
        away = fix["away_team"]
        game_date = pd.to_datetime(fix["date"])
        game_time = str(fix.get("time", ""))
        venue = str(fix.get("venue", "Unknown"))
        referee = str(fix.get("referee", "Unknown"))
        odds_h, odds_d, odds_a = float(fix["odds_home"]), float(fix["odds_draw"]), float(fix["odds_away"])
        raw_h, raw_d, raw_a = 1 / odds_h, 1 / odds_d, 1 / odds_a
        ov = raw_h + raw_d + raw_a
        mkt_h, mkt_d, mkt_a = raw_h / ov, raw_d / ov, raw_a / ov

        h_all = team_form(history, home, game_date)
        a_all = team_form(history, away, game_date)
        h_home = team_form(history, home, game_date, "home")
        a_away = team_form(history, away, game_date, "away")
        data_ok = h_all["n"] >= 3 and a_all["n"] >= 3
        over25_p = avg_rate(h_all.get("over25_rate"), a_all.get("over25_rate"))
        btts_p = avg_rate(h_all.get("btts_rate"), a_all.get("btts_rate"))

        model_h = model_d = model_a = np.nan
        try:
            feat_df = build_fixture_features(history, home, away, game_date, venue, referee, odds_home=odds_h, odds_draw=odds_d, odds_away=odds_a)
            for col in feature_cols:
                if col not in feat_df.columns:
                    feat_df[col] = np.nan
            prob_map = dict(zip(model.classes_, model.predict_proba(feat_df[feature_cols])[0]))
            model_h, model_d, model_a = prob_map.get("H", np.nan), prob_map.get("D", np.nan), prob_map.get("A", np.nan)
        except Exception:
            pass
        if not np.isnan(model_h):
            p_h, p_d, p_a = model_h, model_d, model_a
            prob_src = "model"
        else:
            p_h, p_d, p_a = mkt_h, mkt_d, mkt_a
            prob_src = "market"

        probs_map = {"Home": p_h, "Draw": p_d, "Away": p_a}
        best_1x2 = max(probs_map, key=probs_map.get)
        best_prob = probs_map[best_1x2]
        conf = confidence_label(best_prob, data_ok)
        ctrl, chaos = control_chaos_10(p_h, p_d, p_a, h_all, a_all)

        mkt_map = {"Home": mkt_h, "Draw": mkt_d, "Away": mkt_a}
        mkt_best = max(mkt_map, key=mkt_map.get)
        diverge = (mkt_best != best_1x2) or (abs(best_prob - mkt_map[mkt_best]) > 0.15)
        flags = []
        defensive_weakness = (h_all["ga"] is not None and h_all["ga"] >= 10) or (a_all["ga"] is not None and a_all["ga"] >= 10)
        home_gf_high = h_all["gf"] is not None and h_all["gf"] >= 10
        form_mismatch_H = h_all["pts"] is not None and a_all["pts"] is not None and h_all["pts"] >= 10 and a_all["pts"] <= 5
        both_over = h_all.get("over25_rate") is not None and a_all.get("over25_rate") is not None and h_all["over25_rate"] >= 0.60 and a_all["over25_rate"] >= 0.60
        both_btts = h_all.get("btts_rate") is not None and a_all.get("btts_rate") is not None and h_all["btts_rate"] >= 0.60 and a_all["btts_rate"] >= 0.60
        if home_gf_high: flags.append("home_gf_high")
        if form_mismatch_H: flags.append("form_mismatch_H")
        if both_over: flags.append("both_over")
        if both_btts: flags.append("both_btts")
        if defensive_weakness: flags.append("defensive_weakness")

        profile = build_control_chaos_profile({
            "odds_home": odds_h, "odds_draw": odds_d, "odds_away": odds_a,
            "model_home_prob": p_h, "model_draw_prob": p_d, "model_away_prob": p_a,
            "control_score": ctrl, "chaos_score": chaos, "likely_1x2": best_1x2,
            "both_over": both_over, "both_btts": both_btts, "home_gf_high": home_gf_high, "form_mismatch_H": form_mismatch_H,
        })
        no_conf = conf in ("LOW", "NO-CONFIDENCE") or p_d > 0.30 or ctrl < 2.5
        favorite_strength = profile["home_favorite_strength"] if profile["favorite_side"] == "HOME_FAVORITE" else profile["away_favorite_strength"]
        recommended_market = build_recommended_market({
            "league": "Serie A" if "Serie" in league_name else "Ligue 1",
            "likely_1x2": best_1x2,
            "model_home_prob": p_h,
            "model_draw_prob": p_d,
            "model_away_prob": p_a,
            "odds_home": odds_h,
            "odds_draw": odds_d,
            "odds_away": odds_a,
            "control_score_10": ctrl,
            "chaos_score_10": chaos,
            "confidence": conf,
            "favorite_side": profile["favorite_side"],
            "favorite_strength": favorite_strength,
            "probability_profile": profile["probability_profile"],
            "goals": goals_picture(over25_p, btts_p),
            "over25_signal": over25_signal(over25_p),
            "btts_signal": btts_signal(btts_p),
            "under35_signal": under35_signal(over25_p),
            "data_warning": not data_ok,
            "both_over": both_over,
            "both_btts": both_btts,
            "score_family": profile["score_family"],
        })
        _league_for_profile = "Serie A" if "Serie" in league_name else "Ligue 1"
        recommended_market = apply_league_market_profile(recommended_market, _league_for_profile)
        if not data_ok:
            data_warnings.append(f"{home} vs {away} (home n={h_all['n']}, away n={a_all['n']})")

        print(SEP)
        print(f"  {league_name} {game_time}  |  {home} vs {away}")
        print(SEP)
        print(f"  1X2 PROBABILITIES  [{prob_src}]")
        for label, pval in [("Home", p_h), ("Draw", p_d), ("Away", p_a)]:
            print(f"    {label:<4}: {pval*100:5.1f}%" + (" <--" if label == best_1x2 else ""))
        print(f"  Most likely result : {best_1x2} ({best_prob*100:.1f}%)")
        print(f"  Confidence         : {conf}")
        print(f"\n  Market odds (informative): H {odds_h:.2f}  D {odds_d:.2f}  A {odds_a:.2f}")
        print(f"  Market implied:            H {mkt_h*100:.1f}%  D {mkt_d*100:.1f}%  A {mkt_a*100:.1f}%")
        print(f"  Model predicted:           H {p_h*100:.1f}%  D {p_d*100:.1f}%  A {p_a*100:.1f}%")
        if diverge:
            print(f"  ** WARNING: Model and market disagree (model={best_1x2} {best_prob*100:.0f}%, market={mkt_best} {mkt_map[mkt_best]*100:.0f}%)")
        print(f"\n  GOALS PICTURE  [form-based, last 5 games each team]")
        print(f"    Over 2.5  : {over25_signal(over25_p)}")
        print(f"    BTTS      : {btts_signal(btts_p)}")
        print(f"    Under 3.5 : {under35_signal(over25_p)}")
        print(f"    Most likely score-family: {goals_picture(over25_p, btts_p)}")
        print(f"\n  FORM  [last 5 overall | last 5 venue-specific]")
        for team_name, f_all, f_ven, v_label in [(home, h_all, h_home, "home"), (away, a_all, a_away, "away")]:
            if f_all["n"] >= 3:
                print(f"    {team_name[:30]:<30} [all]   W{f_all['wins']} D{f_all['draws']} L{f_all['losses']}  pts={f_all['pts']}  GF={f_all['gf']:.0f}  GA={f_all['ga']:.0f}  Over25={f_all['over25_rate']*100:.0f}%  BTTS={f_all['btts_rate']*100:.0f}%")
                if f_ven["n"] >= 2:
                    print(f"    {' '*30} [{v_label}]  W{f_ven['wins']} D{f_ven['draws']} L{f_ven['losses']}  pts={f_ven['pts']}  GF={f_ven['gf']:.0f}  GA={f_ven['ga']:.0f}  Over25={f_ven['over25_rate']*100:.0f}%")
                else:
                    print(f"    {' '*30} [{v_label}]  n={f_ven['n']} (insufficient venue data)")
            else:
                print(f"    {team_name[:30]:<30}  ** insufficient history (n={f_all['n']}) **")
        print(f"\n  Pattern flags: {', '.join(flags) if flags else 'none'}")
        print(f"\n  Control Score : {ctrl:4.1f} / 10  [{control_label(ctrl)}]")
        print(f"  Chaos Score   : {chaos:4.1f} / 10  [{chaos_label(chaos)}]")
        print("\n  CONTROL/CHAOS PROFILE  [diagnostic only]")
        for key, value in [
            ("favorite_side", profile["favorite_side"]),
            ("favorite_strength", favorite_strength),
            ("probability_profile", profile["probability_profile"]),
            ("direction_read", profile["direction_read"]),
            ("goals_read", profile["goals_read"]),
            ("risk_warning", profile["risk_warning"]),
            ("score_family", profile["score_family"]),
        ]:
            print(f"    {key:<24}: {value}")
        print("\n  RECOMMENDED MARKET TYPE  [diagnostic only]")
        print(f"    type       : {recommended_market['recommended_market_type']}")
        print(f"    read       : {recommended_market['recommended_market_read']}")
        print(f"    strength   : {recommended_market['recommendation_strength']}")
        print(f"    risk_note  : {recommended_market['risk_note']}")
        print(f"\n  LEAGUE PROFILE  [{league_name} / diagnostic only]")
        print(f"    profile    : {recommended_market['league_profile']}")
        print(f"    adj.strength: {recommended_market['league_adjusted_strength']}")
        print(f"    preferred  : {recommended_market['league_preferred_subtype']}")
        print(f"    suppressed : {recommended_market['league_suppressed_subtype']}")
        if recommended_market['league_warning_flags']:
            print(f"    WARNING    : {recommended_market['league_warning_flags']}")
        if not data_ok:
            print(f"\n  ** DATA WARNING: Insufficient {league_name} history for one or both teams. (home n={h_all['n']}, away n={a_all['n']})")
        if no_conf:
            print(f"\n  ** NO-CONFIDENCE **  Draw p={p_d*100:.0f}% or control={ctrl:.1f}/10 - outcome unclear.")
        print()

        results.append({
            "league": league_name, "home": home, "away": away,
            "p_h": p_h, "p_d": p_d, "p_a": p_a,
            "mkt_h": mkt_h, "mkt_d": mkt_d, "mkt_a": mkt_a,
            "best_1x2": best_1x2, "best_prob": best_prob, "conf": conf,
            "over25_p": over25_p, "btts_p": btts_p, "under35_p": None if over25_p is None else 1 - over25_p,
            "goals_pic": goals_picture(over25_p, btts_p),
            "ctrl": ctrl, "chaos": chaos, "profile": profile,
            "favorite_strength": favorite_strength, "data_ok": data_ok, "no_conf": no_conf,
            "recommended_market": recommended_market,
        })

    print()
    print(SEP)
    print(f"  {league_name.upper()} PRE-MATCH SUMMARY")
    print(SEP)
    print("  Control/Chaos scale: 0-10")
    print(f"  {'Game':<32} {'1X2':>5} {'%':>4} {'Conf':>13} {'Ctrl':>5} {'Chaos':>5} {'Type':<13} {'Strength':<8} Goals")
    print(SEP2)
    for r in results:
        game = f"{r['home'][:14]} vs {r['away'][:14]}"
        rec = r["recommended_market"]
        print(f"  {game:<32} {r['best_1x2']:>5} {r['best_prob']*100:3.0f}% {r['conf']:>13} {r['ctrl']:5.1f} {r['chaos']:5.1f} {rec['recommended_market_type']:<13} {rec['recommendation_strength']:<8} {r['goals_pic']}" + (" *NC*" if r["no_conf"] else ""))

    print()
    print(SEP)
    print(f"  {league_name.upper()} RECOMMENDED MARKET TYPE SUMMARY")
    print(SEP)
    print(f"  {'Match':<34} {'Recommended Type':<16} {'Read':<34} {'Strength':<8} {'Control':>7} {'Chaos':>6} {'Confidence':>13}  Risk Note")
    print(SEP2)
    for r in results:
        game = f"{r['home'][:16]} vs {r['away'][:16]}"
        rec = r["recommended_market"]
        print(f"  {game:<34} {rec['recommended_market_type']:<16} {rec['recommended_market_read']:<34} {rec['recommendation_strength']:<8} {r['ctrl']:7.1f} {r['chaos']:6.1f} {r['conf']:>13}  {rec['risk_note']}")

    print()
    print(SEP)
    print(f"  {league_name.upper()} CONTROL / CHAOS TABLE")
    print(SEP)
    print(f"  {'Match':<34} {'Likely':>6} {'Control':>8} {'Chaos':>7} {'Confidence':>13} {'Fav side':<16} {'Fav strength':<22} {'Profile':<28} Interpretation")
    print(SEP2)
    for r in results:
        game = f"{r['home'][:16]} vs {r['away'][:16]}"
        print(f"  {game:<34} {r['best_1x2']:>6} {r['ctrl']:8.1f} {r['chaos']:7.1f} {r['conf']:>13} {r['profile']['favorite_side']:<16} {r['favorite_strength']:<22} {r['profile']['probability_profile']:<28} {control_chaos_interpretation(r['ctrl'], r['chaos'])}")

    print()
    print(SEP)
    print(f"  {league_name.upper()} FINAL ANALYTICAL REPORT")
    print(SEP)
    cleanest = max([r for r in results if r["data_ok"]] or results, key=lambda r: (r["best_prob"], r["ctrl"] - r["chaos"]))
    highest_control = max(results, key=lambda r: r["ctrl"])
    lowest_control = min(results, key=lambda r: r["ctrl"])
    highest_chaos = max(results, key=lambda r: r["chaos"])
    lowest_chaos = min(results, key=lambda r: r["chaos"])
    most_dangerous = max(results, key=lambda r: (r["chaos"] - r["ctrl"], r["chaos"]))
    print(f"\n  CLEANEST PROBABILITY CALL: {cleanest['home']} vs {cleanest['away']} -> {cleanest['best_1x2']} ({cleanest['best_prob']*100:.1f}%) [{cleanest['conf']}]")
    print(f"  Highest control_score_10: {highest_control['home']} vs {highest_control['away']}  {highest_control['ctrl']:.1f}/10")
    print(f"  Lowest control_score_10 : {lowest_control['home']} vs {lowest_control['away']}  {lowest_control['ctrl']:.1f}/10")
    print(f"  Highest chaos_score_10  : {highest_chaos['home']} vs {highest_chaos['away']}  {highest_chaos['chaos']:.1f}/10")
    print(f"  Lowest chaos_score_10   : {lowest_chaos['home']} vs {lowest_chaos['away']}  {lowest_chaos['chaos']:.1f}/10")
    print(f"  MOST DANGEROUS / UNCLEAR: {most_dangerous['home']} vs {most_dangerous['away']}  chaos={most_dangerous['chaos']:.1f}/10 control={most_dangerous['ctrl']:.1f}/10")
    for title, key, label in [("OVER 2.5", "over25_p", ""), ("BTTS", "btts_p", ""), ("UNDER 3.5", "under35_p", " under-ish")]:
        print(f"\n  {title} RANKING:")
        for r in sorted([x for x in results if x[key] is not None], key=lambda x: x[key], reverse=True):
            print(f"    {r['home'][:17]} vs {r['away'][:17]:<17} {r[key]*100:.0f}%{label}")
    high_conf = [r for r in results if r["conf"] in ("HIGH", "MEDIUM") and r["data_ok"]]
    if high_conf:
        safest = max(high_conf, key=lambda r: r["best_prob"])
        print(f"\n  SAFEST FAVOURITE BY PROBABILITY: {safest['home']} vs {safest['away']} -> {safest['best_1x2']} {safest['best_prob']*100:.1f}% [{safest['conf']}]")
    else:
        print("\n  SAFEST FAVOURITE BY PROBABILITY: none with HIGH/MEDIUM confidence and sufficient data")
    print("\n  DANGEROUS AWAY / UNDERDOG TEAMS:")
    threats = []
    for r in results:
        excess = r["p_a"] * 100 - r["mkt_a"] * 100
        if r["p_a"] * 100 > 35 or excess > 5:
            threats.append((r, excess))
    for r, excess in sorted(threats, key=lambda x: x[0]["p_a"], reverse=True):
        print(f"    {r['away']:<20} @ {r['home']:<20} model_away={r['p_a']*100:.0f}% excess={excess:+.0f}pp")
    if not threats:
        print("    None detected above threshold.")
    print(f"\n  DATA WARNINGS ({len(data_warnings)}):")
    if data_warnings:
        for warning in data_warnings:
            print(f"    {warning}")
    else:
        print("    none")

    return results


def main() -> None:
    bundle = joblib.load(MODEL_FILE)
    all_results = []
    for config in LEAGUES:
        all_results.extend(run_league(config, bundle))

    SEP = "=" * 72
    print()
    print(SEP)
    print("  COMBINED FINAL SHORTLIST  --  SERIE A + LIGUE 1")
    print(SEP)
    low_risk_pool = [r for r in all_results if r["data_ok"]]
    best_direction = max(low_risk_pool or all_results, key=lambda r: (r["best_prob"], r["ctrl"] - r["chaos"]))
    best_over = max([r for r in all_results if r["over25_p"] is not None], key=lambda r: r["over25_p"])
    best_btts = max([r for r in all_results if r["btts_p"] is not None], key=lambda r: r["btts_p"])
    best_under = max([r for r in all_results if r["under35_p"] is not None], key=lambda r: r["under35_p"])
    avoid = sorted(all_results, key=lambda r: (r["no_conf"], r["chaos"] - r["ctrl"], not r["data_ok"]), reverse=True)[:5]
    print(f"  Best low-risk direction : {best_direction['league']} | {best_direction['home']} vs {best_direction['away']} -> {best_direction['best_1x2']} ({best_direction['best_prob']*100:.1f}%, conf={best_direction['conf']}, ctrl={best_direction['ctrl']:.1f}, chaos={best_direction['chaos']:.1f})")
    print(f"  Best Over 2.5           : {best_over['league']} | {best_over['home']} vs {best_over['away']} ({best_over['over25_p']*100:.0f}%)")
    print(f"  Best BTTS               : {best_btts['league']} | {best_btts['home']} vs {best_btts['away']} ({best_btts['btts_p']*100:.0f}%)")
    print(f"  Best Under 3.5          : {best_under['league']} | {best_under['home']} vs {best_under['away']} ({best_under['under35_p']*100:.0f}% under-ish)")
    print("  Games to avoid          :")
    for r in avoid:
        print(f"    {r['league']} | {r['home']} vs {r['away']}  conf={r['conf']} ctrl={r['ctrl']:.1f} chaos={r['chaos']:.1f} profile={r['profile']['probability_profile']}")
    print()
    print(SEP)
    print("  NOTE: Diagnostic probabilities only. No betting, paper-test, ledger, ROI, or value claims.")
    print(SEP)

    # -----------------------------------------------------------------------
    # Save structured CSV for post-match evaluation
    # -----------------------------------------------------------------------
    _out_dir = ROOT / "outputs" / "daily_reports"
    _out_dir.mkdir(parents=True, exist_ok=True)
    _csv_rows = []
    for r in all_results:
        rec = r["recommended_market"]
        _csv_rows.append({
            "date":                      REPORT_DATE,
            "league":                    r.get("league", ""),
            "home_team":                 r["home"],
            "away_team":                 r["away"],
            "likely_1x2":               r["best_1x2"],
            "confidence":                r["conf"],
            "model_home_prob":           round(r["p_h"], 4),
            "model_draw_prob":           round(r["p_d"], 4),
            "model_away_prob":           round(r["p_a"], 4),
            "odds_home":                 r.get("odds_h", ""),
            "odds_draw":                 r.get("odds_d", ""),
            "odds_away":                 r.get("odds_a", ""),
            "control_10":                r["ctrl"],    # already 0-10 in this script
            "chaos_10":                  r["chaos"],
            "over25_p":                  r.get("over25_p"),
            "btts_p":                    r.get("btts_p"),
            "data_ok":                   r.get("data_ok", True),
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
    _csv_path = _out_dir / f"seriea_ligue1_{REPORT_DATE}_daily_report.csv"
    _df.to_csv(_csv_path, index=False)
    print(f"  [CSV saved] {_csv_path}")


if __name__ == "__main__":
    main()
