# -*- coding: utf-8 -*-
"""Daily Probability Report.

Produces a per-game probability snapshot for today's fixtures.
Reports what is most likely -- no ROI / value / paper-test logic.

Usage:
    python scripts/daily_probability_report.py
    python scripts/daily_probability_report.py --fixtures data/upcoming_mls_fixtures_ready.csv
    python scripts/daily_probability_report.py --date 2026-05-18
"""
from __future__ import annotations

import argparse
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
from football_prediction_v19.diagnostics import build_control_chaos_profile, build_recommended_market
from football_prediction_v19.team_names import normalize_team_name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def confidence_label(prob_max: float) -> str:
    if prob_max >= 0.65:
        return "HIGH"
    if prob_max >= 0.50:
        return "MEDIUM"
    return "LOW"


def over25_label(p: float | None) -> str:
    if p is None:
        return "n/a"
    if p >= 0.62:
        return f"OVER  ({p*100:.0f}%)"
    if p <= 0.45:
        return f"UNDER ({p*100:.0f}%)"
    return f"even  ({p*100:.0f}%)"


def btts_label(p: float | None) -> str:
    if p is None:
        return "n/a"
    if p >= 0.60:
        return f"YES  ({p*100:.0f}%)"
    if p <= 0.40:
        return f"NO   ({p*100:.0f}%)"
    return f"even ({p*100:.0f}%)"


def goals_label(over25_p: float | None, btts_p: float | None) -> str:
    """Single most-likely goals picture from the two signals."""
    parts = []
    if over25_p is not None:
        if over25_p >= 0.60:
            parts.append(f"Over2.5 ({over25_p*100:.0f}%)")
        elif over25_p <= 0.42:
            parts.append(f"Under2.5 ({(1-over25_p)*100:.0f}%)")
    if btts_p is not None:
        if btts_p >= 0.58:
            parts.append(f"BTTS ({btts_p*100:.0f}%)")
        elif btts_p <= 0.38:
            parts.append(f"NOT-BTTS ({(1-btts_p)*100:.0f}%)")
    return " + ".join(parts) if parts else "unclear"


# ---------------------------------------------------------------------------
# Form from history
# ---------------------------------------------------------------------------

def team_last5(history: pd.DataFrame, team: str, before_date: pd.Timestamp, n: int = 5) -> dict:
    """Compute last-N stats for a team from combined home+away history."""
    past = history[history["date"] < before_date]

    home_rows = past[past["home_team"] == team].copy()
    home_rows["gf"] = home_rows["home_goals"]
    home_rows["ga"] = home_rows["away_goals"]

    away_rows = past[past["away_team"] == team].copy()
    away_rows["gf"] = away_rows["away_goals"]
    away_rows["ga"] = away_rows["home_goals"]

    combined = pd.concat([home_rows[["date", "gf", "ga"]],
                          away_rows[["date", "gf", "ga"]]], ignore_index=True)
    combined = combined.sort_values("date").tail(n)

    if combined.empty:
        return {"n": 0, "gf": None, "ga": None, "over25_rate": None, "btts_rate": None}

    gf_total = combined["gf"].sum()
    ga_total = combined["ga"].sum()
    over25 = ((combined["gf"] + combined["ga"]) > 2.5).mean()
    btts = ((combined["gf"] > 0) & (combined["ga"] > 0)).mean()

    return {
        "n": len(combined),
        "gf": gf_total,
        "ga": ga_total,
        "over25_rate": round(over25, 3),
        "btts_rate": round(btts, 3),
    }


def compute_over25_prob(h_form: dict, a_form: dict) -> float | None:
    """Estimate Over 2.5 probability from team forms."""
    rates = [r for r in [h_form.get("over25_rate"), a_form.get("over25_rate")]
             if r is not None]
    if not rates:
        return None
    return round(float(np.mean(rates)), 3)


def compute_btts_prob(h_form: dict, a_form: dict) -> float | None:
    rates = [r for r in [h_form.get("btts_rate"), a_form.get("btts_rate")]
             if r is not None]
    if not rates:
        return None
    return round(float(np.mean(rates)), 3)


def compute_control_chaos(h_form: dict, a_form: dict,
                          h_prob: float, a_prob: float, d_prob: float) -> tuple[float, float]:
    """
    Control Score: how clear-cut the match picture is.
      High if one team dominates form AND market.
    Chaos Score: how much uncertainty / surprise potential.
      High if draw probability is elevated AND form is mixed.
    Both 0-100.
    """
    # Market clarity
    max_prob = max(h_prob, a_prob, d_prob)
    control = round((max_prob - 0.33) / (1.0 - 0.33) * 100, 1)
    control = max(0.0, min(100.0, control))

    # Chaos: elevated draw + mixed over25 rates
    draw_weight = d_prob * 100
    over25_h = h_form.get("over25_rate") or 0.5
    over25_a = a_form.get("over25_rate") or 0.5
    form_variance = abs(over25_h - over25_a) * 100
    chaos = round((draw_weight * 0.6 + form_variance * 0.4), 1)
    chaos = max(0.0, min(100.0, chaos))

    return control, chaos


# ---------------------------------------------------------------------------
# Load model
# ---------------------------------------------------------------------------

def load_model(model_path: Path) -> dict:
    obj = joblib.load(model_path)
    if isinstance(obj, dict) and "model" in obj:
        return obj
    raise ValueError(f"Unexpected model format in {model_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Daily Probability Report")
    parser.add_argument("--fixtures", default=None,
                        help="Fixture CSV. If omitted, auto-detect from data/")
    parser.add_argument("--history", default=str(ROOT / "data/processed/matches_clean_with_totals.csv"),
                        help="Historical match file with goals (default: matches_clean_with_totals.csv)")
    parser.add_argument("--model", default=str(ROOT / "models/real_model.joblib"),
                        help="Model file (default: real_model.joblib)")
    parser.add_argument("--date", default=None,
                        help="Target date YYYY-MM-DD (default: today)")
    args = parser.parse_args()

    target_date = pd.Timestamp(args.date) if args.date else pd.Timestamp.today().normalize()
    date_str = target_date.strftime("%Y-%m-%d")

    # ---- Auto-detect fixture files ----
    fixture_files = []
    if args.fixtures:
        fixture_files = [Path(args.fixtures)]
    else:
        candidates = [
            ROOT / "data" / "upcoming_mls_fixtures_ready.csv",
            ROOT / "data" / "upcoming_serie_a_fixtures_ready.csv",
        ]
        for c in candidates:
            if c.exists():
                fixture_files.append(c)
        if not fixture_files:
            print("No fixture files found. Pass --fixtures <file>.")
            sys.exit(1)

    # ---- Load history ----
    hist_path = Path(args.history)
    if not hist_path.exists():
        print(f"ERROR: History file not found: {hist_path}", file=sys.stderr)
        sys.exit(1)
    history = pd.read_csv(hist_path, parse_dates=["date"])
    history["home_team"] = history["home_team"].apply(normalize_team_name)
    history["away_team"] = history["away_team"].apply(normalize_team_name)

    # ---- Load model ----
    model_path = Path(args.model)
    try:
        model_bundle = load_model(model_path)
        model = model_bundle["model"]
        feature_cols = model_bundle["feature_cols"]
        model_ok = True
    except Exception as e:
        print(f"WARNING: Could not load model ({e}). 1X2 probabilities will use market odds only.")
        model_ok = False

    # ---- Load and combine fixtures ----
    fixture_frames = []
    for ff in fixture_files:
        try:
            df = pd.read_csv(ff, parse_dates=["date"])
            # Filter to target date (or keep all if date not deterministic)
            if "date" in df.columns:
                df_today = df[df["date"].dt.date == target_date.date()]
                if df_today.empty:
                    print(f"  [{ff.name}]: no games on {date_str} (file has {len(df)} rows total, using all)")
                    df_today = df  # fallback: show all
                fixture_frames.append(df_today)
            else:
                fixture_frames.append(df)
        except Exception as e:
            print(f"WARNING: Could not read {ff}: {e}")

    if not fixture_frames:
        print("No fixtures to report.")
        sys.exit(0)

    fixtures = pd.concat(fixture_frames, ignore_index=True)
    fixtures["home_team"] = fixtures["home_team"].apply(normalize_team_name)
    fixtures["away_team"] = fixtures["away_team"].apply(normalize_team_name)

    # ---- Report header ----
    sep_thick = "=" * 72
    sep_thin = "-" * 72

    print()
    print(sep_thick)
    print(f"  DAILY PROBABILITY REPORT  --  {date_str}")
    print(f"  History: {len(history)} matches across {len(fixture_files)} source file(s)")
    print(f"  Model: {model_path.name}  |  Fixtures: {len(fixtures)} games")
    print(sep_thick)
    print()
    print("  IMPORTANT: This report shows probability estimates only.")
    print("  No value, ROI, or profitability claims are made.")
    print()

    all_results = []

    for _, fix in fixtures.iterrows():
        home = fix["home_team"]
        away = fix["away_team"]
        league = fix.get("league", "Unknown")
        game_date = pd.to_datetime(fix.get("date", target_date))
        game_time = fix.get("time", "")

        odds_h = pd.to_numeric(fix.get("odds_home"), errors="coerce")
        odds_d = pd.to_numeric(fix.get("odds_draw"), errors="coerce")
        odds_a = pd.to_numeric(fix.get("odds_away"), errors="coerce")

        # ---- Market implied probabilities (overround-adjusted) ----
        if pd.notna(odds_h) and pd.notna(odds_d) and pd.notna(odds_a):
            raw_h = 1 / odds_h
            raw_d = 1 / odds_d
            raw_a = 1 / odds_a
            overround = raw_h + raw_d + raw_a
            mkt_h = raw_h / overround
            mkt_d = raw_d / overround
            mkt_a = raw_a / overround
        else:
            mkt_h = mkt_d = mkt_a = None

        # ---- Model 1X2 probabilities ----
        model_h = model_d = model_a = None
        if model_ok:
            try:
                feat_df = build_fixture_features(
                    history_df=history,
                    home_team=home,
                    away_team=away,
                    match_date=game_date,
                    venue=str(fix.get("venue", "Unknown")),
                    referee=str(fix.get("referee", "Unknown")),
                    odds_home=float(odds_h) if pd.notna(odds_h) else None,
                    odds_draw=float(odds_d) if pd.notna(odds_d) else None,
                    odds_away=float(odds_a) if pd.notna(odds_a) else None,
                )
                # Fill missing feature cols with NaN
                for col in feature_cols:
                    if col not in feat_df.columns:
                        feat_df[col] = np.nan
                X = feat_df[feature_cols]
                proba = model.predict_proba(X)[0]
                classes = model.classes_
                prob_map = dict(zip(classes, proba))
                model_h = prob_map.get("H", np.nan)
                model_d = prob_map.get("D", np.nan)
                model_a = prob_map.get("A", np.nan)
            except Exception as e:
                model_h = model_d = model_a = None

        # ---- Best 1X2 probability estimate ----
        # Prefer model if available, fall back to market
        if model_h is not None and not np.isnan(model_h):
            p_h, p_d, p_a = model_h, model_d, model_a
            prob_source = "model"
        elif mkt_h is not None:
            p_h, p_d, p_a = mkt_h, mkt_d, mkt_a
            prob_source = "market"
        else:
            p_h = p_d = p_a = None
            prob_source = "none"

        # ---- Form features from history ----
        h_form = team_last5(history, home, game_date)
        a_form = team_last5(history, away, game_date)

        over25_prob = compute_over25_prob(h_form, a_form)
        btts_prob = compute_btts_prob(h_form, a_form)

        # ---- Pattern flags ----
        h_gf5 = h_form.get("gf")
        a_gf5 = a_form.get("gf")
        h_over_rate = h_form.get("over25_rate")
        a_over_rate = a_form.get("over25_rate")

        home_gf_high = (h_gf5 is not None and h_gf5 >= 10)
        form_mismatch_H = False
        if p_h is not None:
            h_pts_proxy = (h_over_rate or 0.5) * 15  # rough
            a_pts_proxy = (a_over_rate or 0.5) * 15
        # Use h_pts from form directly if available
        h_pts_est = None
        a_pts_est = None
        hist_home = history[
            (history["home_team"] == home) & (history["date"] < game_date)
        ].tail(5)
        hist_away_as_home = history[
            (history["away_team"] == home) & (history["date"] < game_date)
        ].tail(5)
        # Compute actual pts last 5 for home team
        def pts_from_rows(home_rows, away_rows, team):
            results = []
            for _, r in home_rows.iterrows():
                if r["home_goals"] > r["away_goals"]:
                    results.append(3)
                elif r["home_goals"] == r["away_goals"]:
                    results.append(1)
                else:
                    results.append(0)
            for _, r in away_rows.iterrows():
                if r["away_goals"] > r["home_goals"]:
                    results.append(3)
                elif r["away_goals"] == r["home_goals"]:
                    results.append(1)
                else:
                    results.append(0)
            combined = sorted(pd.concat([home_rows["date"], away_rows["date"]]).values)[-5:]
            return sum(results[-5:]) if results else None

        h_as_home = history[(history["home_team"] == home) & (history["date"] < game_date)]
        h_as_away = history[(history["away_team"] == home) & (history["date"] < game_date)]
        a_as_home = history[(history["home_team"] == away) & (history["date"] < game_date)]
        a_as_away = history[(history["away_team"] == away) & (history["date"] < game_date)]

        def last5_pts(as_home, as_away):
            parts = []
            for _, r in as_home.iterrows():
                g = r.get("home_goals", np.nan)
                ag = r.get("away_goals", np.nan)
                if pd.notna(g) and pd.notna(ag):
                    parts.append((r["date"], 3 if g > ag else (1 if g == ag else 0)))
            for _, r in as_away.iterrows():
                g = r.get("away_goals", np.nan)
                ag = r.get("home_goals", np.nan)
                if pd.notna(g) and pd.notna(ag):
                    parts.append((r["date"], 3 if g > ag else (1 if g == ag else 0)))
            parts.sort(key=lambda x: x[0])
            return sum(p[1] for p in parts[-5:]) if parts else None

        h_pts5 = last5_pts(h_as_home, h_as_away)
        a_pts5 = last5_pts(a_as_home, a_as_away)
        form_mismatch_H = (h_pts5 is not None and a_pts5 is not None
                           and h_pts5 >= 10 and a_pts5 <= 5)
        both_over_flag = (h_over_rate is not None and a_over_rate is not None
                          and h_over_rate >= 0.6 and a_over_rate >= 0.6)

        # ---- Control & Chaos scores ----
        if p_h is not None:
            control, chaos = compute_control_chaos(h_form, a_form, p_h, p_d, p_a)
        else:
            control = chaos = None

        # ---- Most likely 1X2 result ----
        if p_h is not None:
            probs_1x2 = {"Home": p_h, "Draw": p_d, "Away": p_a}
            best_1x2 = max(probs_1x2, key=probs_1x2.get)
            best_prob = probs_1x2[best_1x2]
            conf = confidence_label(best_prob)
        else:
            best_1x2 = "Unknown"
            best_prob = None
            conf = "LOW"

        no_confidence = (conf == "LOW" or
                         (p_d is not None and p_d > 0.35) or
                         (control is not None and control < 20))

        all_results.append({
            "league": league,
            "time": game_time,
            "home": home,
            "away": away,
            "p_h": p_h, "p_d": p_d, "p_a": p_a,
            "prob_source": prob_source,
            "best_1x2": best_1x2,
            "best_prob": best_prob,
            "conf": conf,
            "no_confidence": no_confidence,
            "over25_prob": over25_prob,
            "btts_prob": btts_prob,
            "h_gf5": h_gf5,
            "a_gf5": a_gf5,
            "h_over_rate": h_over_rate,
            "a_over_rate": a_over_rate,
            "h_pts5": h_pts5,
            "a_pts5": a_pts5,
            "h_n": h_form["n"],
            "a_n": a_form["n"],
            "home_gf_high": home_gf_high,
            "form_mismatch_H": form_mismatch_H,
            "both_over": both_over_flag,
            "control": control,
            "chaos": chaos,
            "odds_h": odds_h, "odds_d": odds_d, "odds_a": odds_a,
            "mkt_h": mkt_h, "mkt_d": mkt_d, "mkt_a": mkt_a,
        })

    # ---- Print games ----
    for r in all_results:
        time_str = f" {r['time']}" if r['time'] else ""
        print(sep_thick)
        print(f"  {r['league']}{time_str}  |  {r['home']} vs {r['away']}")
        print(sep_thick)

        # 1X2 probabilities
        print(f"  1X2 PROBABILITIES  [{r['prob_source']}]")
        if r["p_h"] is not None:
            marker_h = " <--" if r["best_1x2"] == "Home" else ""
            marker_d = " <--" if r["best_1x2"] == "Draw" else ""
            marker_a = " <--" if r["best_1x2"] == "Away" else ""
            print(f"    Home : {r['p_h']*100:5.1f}%{marker_h}")
            print(f"    Draw : {r['p_d']*100:5.1f}%{marker_d}")
            print(f"    Away : {r['p_a']*100:5.1f}%{marker_a}")
            print(f"  Most likely result : {r['best_1x2']} ({r['best_prob']*100:.1f}%)")
            print(f"  Confidence         : {r['conf']}")
        else:
            print("    No model or market odds available.")

        # Market odds (informative only)
        if r["odds_h"] is not None:
            print(f"\n  Market odds (informative): "
                  f"H {r['odds_h']:.2f}  D {r['odds_d']:.2f}  A {r['odds_a']:.2f}")
            if r["mkt_h"] is not None:
                print(f"  Market implied:            "
                      f"H {r['mkt_h']*100:.1f}%  D {r['mkt_d']*100:.1f}%  A {r['mkt_a']*100:.1f}%")

        # Goals picture
        print(f"\n  GOALS PICTURE  [form-based, last 5 games]")
        print(f"    Over 2.5     : {over25_label(r['over25_prob'])}")
        print(f"    BTTS         : {btts_label(r['btts_prob'])}")
        goals_str = goals_label(r["over25_prob"], r["btts_prob"])
        print(f"    Most likely  : {goals_str}" if goals_str else "")

        # Form details
        print(f"\n  FORM  [last 5 each team]")
        h_n = r["h_n"]
        a_n = r["a_n"]
        if h_n >= 3:
            print(f"    {r['home'][:28]:<28}  GF={r['h_gf5']:4.0f}  Over25={r['h_over_rate']*100:.0f}%  pts5={r['h_pts5'] if r['h_pts5'] is not None else 'n/a'}")
        else:
            print(f"    {r['home'][:28]:<28}  insufficient history (n={h_n})")
        if a_n >= 3:
            print(f"    {r['away'][:28]:<28}  GF={r['a_gf5']:4.0f}  Over25={r['a_over_rate']*100:.0f}%  pts5={r['a_pts5'] if r['a_pts5'] is not None else 'n/a'}")
        else:
            print(f"    {r['away'][:28]:<28}  insufficient history (n={a_n})")

        # Pattern flags
        flags = []
        if r["home_gf_high"]:
            flags.append("home_gf_high")
        if r["form_mismatch_H"]:
            flags.append("form_mismatch_H")
        if r["both_over"]:
            flags.append("both_over")
        print(f"    Flags: {', '.join(flags) if flags else 'none'}")

        # Control / Chaos
        if r["control"] is not None:
            ctrl_bar = "#" * int(r["control"] / 10)
            chaos_bar = "#" * int(r["chaos"] / 10)
            print(f"\n  Control Score : {r['control']:5.1f} / 100  [{ctrl_bar:<10}]")
            print(f"  Chaos Score   : {r['chaos']:5.1f} / 100  [{chaos_bar:<10}]")
            diagnostic_profile = build_control_chaos_profile({
                "odds_home": r["odds_h"],
                "odds_draw": r["odds_d"],
                "odds_away": r["odds_a"],
                "model_home_prob": r["p_h"],
                "model_draw_prob": r["p_d"],
                "model_away_prob": r["p_a"],
                "control_score": r["control"] / 10,
                "chaos_score": r["chaos"] / 10,
                "likely_1x2": r["best_1x2"],
                "both_over": r["both_over"],
                "both_btts": r["btts_prob"] is not None and r["btts_prob"] >= 0.60,
                "home_gf_high": r["home_gf_high"],
                "form_mismatch_H": r["form_mismatch_H"],
            })
            print("\n  CONTROL/CHAOS PROFILE  [diagnostic only]")
            print(f"    probability_profile : {diagnostic_profile['probability_profile']}")
            print(f"    direction_read      : {diagnostic_profile['direction_read']}")
            print(f"    goals_read          : {diagnostic_profile['goals_read']}")
            print(f"    risk_warning        : {diagnostic_profile['risk_warning']}")
            print(f"    score_family        : {diagnostic_profile['score_family']}")
            favorite_strength = diagnostic_profile["home_favorite_strength"] if diagnostic_profile["favorite_side"] == "HOME_FAVORITE" else diagnostic_profile["away_favorite_strength"]
            recommended_market = build_recommended_market({
                "league": r["league"],
                "likely_1x2": r["best_1x2"],
                "model_home_prob": r["p_h"],
                "model_draw_prob": r["p_d"],
                "model_away_prob": r["p_a"],
                "odds_home": r["odds_h"],
                "odds_draw": r["odds_d"],
                "odds_away": r["odds_a"],
                "control_score_10": r["control"] / 10,
                "chaos_score_10": r["chaos"] / 10,
                "confidence": r["conf"],
                "favorite_side": diagnostic_profile["favorite_side"],
                "favorite_strength": favorite_strength,
                "probability_profile": diagnostic_profile["probability_profile"],
                "goals": goals_str,
                "over25_signal": over25_label(r["over25_prob"]),
                "btts_signal": btts_label(r["btts_prob"]),
                "data_warning": h_n < 3 or a_n < 3,
                "both_over": r["both_over"],
                "both_btts": r["btts_prob"] is not None and r["btts_prob"] >= 0.60,
                "score_family": diagnostic_profile["score_family"],
            })
            r["recommended_market"] = recommended_market
            print("\n  RECOMMENDED MARKET TYPE  [diagnostic only]")
            print(f"    type       : {recommended_market['recommended_market_type']}")
            print(f"    read       : {recommended_market['recommended_market_read']}")
            print(f"    strength   : {recommended_market['recommendation_strength']}")
            print(f"    risk_note  : {recommended_market['risk_note']}")

        # No-confidence flag
        if r["no_confidence"]:
            print(f"\n  ** NO-CONFIDENCE **  Draw probability or uncertainty is elevated.")

        print()

    # ---- Summary table ----
    print()
    print(sep_thick)
    print("  SUMMARY")
    print(sep_thick)
    print(f"  {'Game':<40} {'Result':>6}  {'Conf':>6}  {'Type':<13} {'Strength':<8} {'Goals':<18}  {'NC'}")
    print(sep_thin)
    for r in all_results:
        game_str = f"{r['home'][:17]} vs {r['away'][:17]}"
        result_str = r["best_1x2"] if r["best_1x2"] != "Unknown" else "?"
        conf_str = r["conf"]
        g_str = goals_label(r["over25_prob"], r["btts_prob"])
        nc_str = "** NC **" if r["no_confidence"] else ""
        rec = r.get("recommended_market", {"recommended_market_type": "OBSERVE_ONLY", "recommendation_strength": "LOW"})
        print(f"  {game_str:<40} {result_str:>6}  {conf_str:>6}  {rec['recommended_market_type']:<13} {rec['recommendation_strength']:<8} {g_str:<18}  {nc_str}")

    print()
    print(sep_thick)
    print("  RECOMMENDED MARKET TYPE SUMMARY")
    print(sep_thick)
    print(f"  {'Match':<40} {'Recommended Type':<16} {'Read':<34} {'Strength':<8} {'Control':>7} {'Chaos':>6} {'Confidence':>10}  Risk Note")
    print(sep_thin)
    for r in all_results:
        game_str = f"{r['home'][:17]} vs {r['away'][:17]}"
        rec = r.get("recommended_market", {"recommended_market_type": "OBSERVE_ONLY", "recommended_market_read": "not_available", "recommendation_strength": "LOW", "risk_note": "not_available"})
        ctrl = r["control"] / 10 if r["control"] is not None else 0
        chaos = r["chaos"] / 10 if r["chaos"] is not None else 0
        print(f"  {game_str:<40} {rec['recommended_market_type']:<16} {rec['recommended_market_read']:<34} {rec['recommendation_strength']:<8} {ctrl:7.1f} {chaos:6.1f} {r['conf']:>10}  {rec['risk_note']}")

    # ---- No-confidence games ----
    nc_games = [r for r in all_results if r["no_confidence"]]
    if nc_games:
        print()
        print(sep_thin)
        print(f"  NO-CONFIDENCE GAMES ({len(nc_games)}/{len(all_results)}):")
        for r in nc_games:
            print(f"    {r['home']} vs {r['away']}  --  draw p={r['p_d']*100:.1f}% / control={r['control']:.0f}/100" if r['p_d'] else f"    {r['home']} vs {r['away']}")

    print()
    print(sep_thick)
    print("  NOTE: Probabilities are model/market estimates, not guarantees.")
    print("  Over 2.5 / BTTS probabilities are based on rolling form rates only.")
    print("  Real bookmaker Over 2.5 odds already price in form (see audit).")
    print("  No betting, paper-test, or profitability claims are made here.")
    print(sep_thick)
    print()


if __name__ == "__main__":
    main()
