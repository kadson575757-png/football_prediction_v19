# -*- coding: utf-8 -*-
"""MLS daily probability report for the final fixtures before the 2026 break.

Diagnostic only: no betting logic, no staking, no ROI, no probability changes.

Usage:
    python scripts/mls_daily_probability_report.py
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

from football_prediction_v19.diagnostics import (
    apply_league_market_profile,
    build_control_chaos_profile,
    build_market_tier,
    build_recommended_market,
)
from football_prediction_v19.features import build_fixture_features
from football_prediction_v19.reports.watchlist import append_watchlist_to_report
from football_prediction_v19.team_names import normalize_team_name

LEAGUE_NAME = "MLS"
LEAGUE_TAG = "mls"
TARGET_DATES = (pd.Timestamp("2026-05-23").date(), pd.Timestamp("2026-05-24").date())

FIXTURE_FILE = ROOT / "data" / "upcoming_mls_fixtures.csv"
MODEL_FILE = ROOT / "outputs" / "model_comparison_top5" / "best_model.joblib"

HIST_RAW_2025 = ROOT / "data" / "raw" / "football_data_MLS_2025.csv"
HIST_RAW_2026 = ROOT / "data" / "raw" / "football_data_MLS_2026.csv"
HIST_PROCESSED = ROOT / "data" / "processed" / "mls_clean.csv"

MISSING_HISTORY_ERROR = (
    "MLS historical data missing. Create data/raw/football_data_MLS_2025.csv "
    "or data/raw/football_data_MLS_2026.csv with Date,HomeTeam,AwayTeam,FTHG,"
    "FTAG,FTR and optional B365H/B365D/B365A."
)


def confidence_label(p_max: float, data_ok: bool) -> str:
    if not data_ok:
        return "NO-CONFIDENCE"
    if p_max >= 0.65:
        return "HIGH"
    if p_max >= 0.50:
        return "MEDIUM"
    return "LOW"


def _float_or_default(value: object, default: float) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def over25_signal(p: float | None) -> str:
    if p is None:
        return "n/a"
    if p >= 0.62:
        return f"OVER likely ({p * 100:.0f}%)"
    if p <= 0.42:
        return f"UNDER likely ({(1 - p) * 100:.0f}% under)"
    return f"unclear ({p * 100:.0f}% over)"


def btts_signal(p: float | None) -> str:
    if p is None:
        return "n/a"
    if p >= 0.60:
        return f"BTTS YES likely ({p * 100:.0f}%)"
    if p <= 0.38:
        return f"BTTS NO likely ({(1 - p) * 100:.0f}% no-btts)"
    return f"unclear ({p * 100:.0f}% btts)"


def goals_picture(over25_p: float | None, btts_p: float | None) -> str:
    parts: list[str] = []
    if over25_p is not None:
        if over25_p >= 0.62:
            parts.append(f"Over2.5 ({over25_p * 100:.0f}%)")
        elif over25_p <= 0.42:
            parts.append(f"Under2.5 ({(1 - over25_p) * 100:.0f}%)")
    if btts_p is not None:
        if btts_p >= 0.58:
            parts.append(f"BTTS ({btts_p * 100:.0f}%)")
        elif btts_p <= 0.38:
            parts.append(f"NOT-BTTS ({(1 - btts_p) * 100:.0f}%)")
    return " + ".join(parts) if parts else "unclear"


def avg_rate(a: float | None, b: float | None) -> float | None:
    vals = [v for v in (a, b) if v is not None]
    return round(float(np.mean(vals)), 3) if vals else None


def load_history() -> pd.DataFrame:
    raw_parts = [pd.read_csv(p) for p in (HIST_RAW_2025, HIST_RAW_2026) if p.exists()]
    if raw_parts:
        raw = pd.concat(raw_parts, ignore_index=True)
        col_map = {
            "Date": "date",
            "HomeTeam": "home_team",
            "AwayTeam": "away_team",
            "FTHG": "home_goals",
            "FTAG": "away_goals",
            "FTR": "result",
            "B365H": "odds_home",
            "B365D": "odds_draw",
            "B365A": "odds_away",
        }
        history = raw.rename(columns={k: v for k, v in col_map.items() if k in raw.columns})
        required = {"date", "home_team", "away_team", "home_goals", "away_goals", "result"}
        missing = required.difference(history.columns)
        if missing:
            raise FileNotFoundError(MISSING_HISTORY_ERROR)
        history["date"] = pd.to_datetime(history["date"], dayfirst=True, errors="coerce")
    elif HIST_PROCESSED.exists():
        history = pd.read_csv(HIST_PROCESSED, parse_dates=["date"])
    else:
        raise FileNotFoundError(MISSING_HISTORY_ERROR)

    history = history.dropna(subset=["date", "home_team", "away_team", "home_goals", "away_goals"]).copy()
    history["home_team"] = history["home_team"].apply(normalize_team_name)
    history["away_team"] = history["away_team"].apply(normalize_team_name)
    return history


def load_fixtures() -> pd.DataFrame:
    if not FIXTURE_FILE.exists():
        return pd.DataFrame()
    fixtures = pd.read_csv(FIXTURE_FILE, parse_dates=["date"])
    fixtures["home_team"] = fixtures["home_team"].apply(normalize_team_name)
    fixtures["away_team"] = fixtures["away_team"].apply(normalize_team_name)
    return fixtures[fixtures["date"].dt.date.isin(TARGET_DATES)].reset_index(drop=True)


def load_model_bundle() -> dict:
    if not MODEL_FILE.exists():
        raise FileNotFoundError(f"[ERROR] No model file found: {MODEL_FILE}")
    return joblib.load(MODEL_FILE)


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
    return {
        "n": len(rows),
        "wins": int((gf > ga).sum()),
        "draws": int((gf == ga).sum()),
        "losses": int((gf < ga).sum()),
        "pts": int((gf > ga).sum()) * 3 + int((gf == ga).sum()),
        "gf": float(gf.sum()),
        "ga": float(ga.sum()),
        "over25_rate": round(float(((gf + ga) > 2.5).mean()), 3),
        "btts_rate": round(float(((gf > 0) & (ga > 0)).mean()), 3),
    }


def build_report_rows(history: pd.DataFrame, fixtures: pd.DataFrame, bundle: dict) -> list[dict]:
    model = bundle["model"]
    feature_cols = bundle["feature_cols"]
    rows: list[dict] = []

    for _, fix in fixtures.iterrows():
        home = fix["home_team"]
        away = fix["away_team"]
        game_date = pd.to_datetime(fix["date"])
        odds_h = _float_or_default(fix.get("odds_home"), 2.0)
        odds_d = _float_or_default(fix.get("odds_draw"), 3.3)
        odds_a = _float_or_default(fix.get("odds_away"), 3.5)
        venue = str(fix.get("venue", "Unknown"))
        referee = str(fix.get("referee", "Unknown"))

        raw_h, raw_d, raw_a = 1 / odds_h, 1 / odds_d, 1 / odds_a
        overround = raw_h + raw_d + raw_a
        mkt_h, mkt_d, mkt_a = raw_h / overround, raw_d / overround, raw_a / overround

        h_all = team_form(history, home, game_date)
        a_all = team_form(history, away, game_date)
        data_ok = h_all["n"] >= 3 and a_all["n"] >= 3
        over25_p = avg_rate(h_all.get("over25_rate"), a_all.get("over25_rate"))
        btts_p = avg_rate(h_all.get("btts_rate"), a_all.get("btts_rate"))

        model_h = model_d = model_a = np.nan
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
            proba = model.predict_proba(feat_df[feature_cols])[0]
            prob_map = dict(zip(model.classes_, proba))
            model_h = prob_map.get("H", np.nan)
            model_d = prob_map.get("D", np.nan)
            model_a = prob_map.get("A", np.nan)
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
        ctrl = round(max(0, min(100, (max(p_h, p_d, p_a) - 0.33) / 0.67 * 100)), 1)
        chaos = round(max(0, min(100, p_d * 60 + abs((h_all.get("over25_rate") or 0.5) - (a_all.get("over25_rate") or 0.5)) * 40)), 1)

        both_over = bool(h_all.get("over25_rate") is not None and a_all.get("over25_rate") is not None and h_all["over25_rate"] >= 0.60 and a_all["over25_rate"] >= 0.60)
        both_btts = bool(h_all.get("btts_rate") is not None and a_all.get("btts_rate") is not None and h_all["btts_rate"] >= 0.60 and a_all["btts_rate"] >= 0.60)
        goals = goals_picture(over25_p, btts_p)

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
            "both_over": both_over,
            "both_btts": both_btts,
        })
        fav_strength = (
            diagnostic_profile["home_favorite_strength"]
            if diagnostic_profile["favorite_side"] == "HOME_FAVORITE"
            else diagnostic_profile["away_favorite_strength"]
        )

        rec = build_recommended_market({
            "league": LEAGUE_NAME,
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
            "favorite_strength": fav_strength,
            "probability_profile": diagnostic_profile["probability_profile"],
            "goals": goals,
            "over25_signal": over25_signal(over25_p),
            "btts_signal": btts_signal(btts_p),
            "data_warning": not data_ok,
            "both_over": both_over,
            "both_btts": both_btts,
            "score_family": diagnostic_profile["score_family"],
        })
        rec = apply_league_market_profile(rec, LEAGUE_NAME)
        rec = build_market_tier(rec)

        rows.append({
            "date": game_date.strftime("%Y-%m-%d"),
            "league": LEAGUE_NAME,
            "home_team": home,
            "away_team": away,
            "likely_1x2": best_1x2,
            "confidence": conf,
            "model_home_prob": round(float(p_h), 4),
            "model_draw_prob": round(float(p_d), 4),
            "model_away_prob": round(float(p_a), 4),
            "odds_home": odds_h,
            "odds_draw": odds_d,
            "odds_away": odds_a,
            "prob_src": prob_src,
            "control_10": round(ctrl / 10, 2),
            "chaos_10": round(chaos / 10, 2),
            "over25_p": over25_p,
            "btts_p": btts_p,
            "data_ok": data_ok,
            "recommended_market_type": rec["recommended_market_type"],
            "recommended_market_subtype": rec.get("recommended_market_subtype", "NONE"),
            "recommended_market_read": rec["recommended_market_read"],
            "recommendation_strength": rec["recommendation_strength"],
            "risk_note": rec["risk_note"],
            "league_profile": rec.get("league_profile", ""),
            "league_adjusted_strength": rec.get("league_adjusted_strength", ""),
            "league_profile_note": rec.get("league_profile_note", ""),
            "league_warning_flags": rec.get("league_warning_flags", ""),
            "league_preferred_subtype": rec.get("league_preferred_subtype", ""),
            "league_suppressed_subtype": rec.get("league_suppressed_subtype", ""),
            "market_tier": rec.get("market_tier", ""),
            "market_tier_score": rec.get("market_tier_score", ""),
            "market_tier_reason": rec.get("market_tier_reason", ""),
            "market_tier_flags": rec.get("market_tier_flags", ""),
        })
    return rows


def write_daily_reports(rows: list[dict]) -> list[Path]:
    out_dir = ROOT / "outputs" / "daily_reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    if not rows:
        return written
    df = pd.DataFrame(rows)
    for report_date, date_df in df.groupby("date", sort=True):
        csv_path = out_dir / f"{LEAGUE_TAG}_{report_date}_daily_report.csv"
        date_df.to_csv(csv_path, index=False)
        append_watchlist_to_report(str(csv_path), date_df.to_dict("records"))
        written.append(csv_path)
    return written


def main() -> int:
    print("MLS DAILY PROBABILITY REPORT - diagnostic only")
    print("No betting logic, staking, ROI, or probability logic changes.")
    try:
        history = load_history()
        fixtures = load_fixtures()
        bundle = load_model_bundle()
    except FileNotFoundError as exc:
        print(str(exc))
        return 1

    print(f"History: {len(history)} MLS matches")
    print(f"Fixtures: {len(fixtures)} across 2026-05-23 and 2026-05-24")
    if fixtures.empty:
        print("No MLS fixtures found for target dates.")
        return 0

    rows = build_report_rows(history, fixtures, bundle)
    written = write_daily_reports(rows)
    for path in written:
        print(f"[CSV saved] {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
