# -*- coding: utf-8 -*-
"""Historical control/chaos x favorite-strength audit.

Diagnostic only. No betting rules, paper-test rules, ledger entries, or ROI claims.
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

from football_prediction_v19.features import build_features
from football_prediction_v19.rules_v19 import assess_prediction
from football_prediction_v19.team_names import normalize_team_name

OUT_DIR = ROOT / "outputs" / "diagnostics"
AUDIT_CSV = OUT_DIR / "control_chaos_strength_audit.csv"
SUMMARY_MD = OUT_DIR / "control_chaos_strength_summary.md"

DATA_SOURCES = [
    ROOT / "data" / "processed" / "all_leagues_2021_2025_clean.csv",
    ROOT / "data" / "processed" / "mls_matches_clean_with_odds.csv",
]

MODEL_SOURCES = {
    "MLS": ROOT / "outputs" / "model_comparison_mls_2025" / "best_model.joblib",
    "2. Bundesliga": ROOT / "outputs" / "model_comparison_d2" / "best_model.joblib",
    "Eredivisie": ROOT / "outputs" / "model_comparison_eredivisie" / "best_model.joblib",
    "default": ROOT / "outputs" / "model_comparison_top5" / "best_model.joblib",
}

LEAGUE_DISPLAY = {
    "MLS": "MLS",
    "2. Bundesliga": "D2",
    "Eredivisie": "Eredivisie",
    "Premier League": "Premier League",
    "Serie A": "Serie A",
    "Bundesliga": "Bundesliga",
    "La Liga": "La Liga",
    "Ligue 1": "Ligue 1",
}


def load_matches() -> tuple[pd.DataFrame, list[str]]:
    frames = []
    used = []
    for path in DATA_SOURCES:
        if not path.exists():
            continue
        df = pd.read_csv(path, parse_dates=["date"])
        df["source_file"] = path.name
        frames.append(df)
        used.append(str(path.relative_to(ROOT)))
    if not frames:
        raise FileNotFoundError("No historical data sources found.")

    df = pd.concat(frames, ignore_index=True)
    required = ["date", "home_team", "away_team", "home_goals", "away_goals", "odds_home", "odds_draw", "odds_away"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    df["home_team"] = df["home_team"].astype(str).apply(normalize_team_name)
    df["away_team"] = df["away_team"].astype(str).apply(normalize_team_name)
    for col in ["home_goals", "away_goals", "odds_home", "odds_draw", "odds_away"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=required)
    df = df[(df["odds_home"] > 1.0) & (df["odds_draw"] > 1.0) & (df["odds_away"] > 1.0)]
    df = df.drop_duplicates(subset=["date", "league", "home_team", "away_team"]).sort_values(["date", "league", "home_team"]).reset_index(drop=True)
    return df, used


def load_models() -> dict[str, dict]:
    bundles = {}
    for league, path in MODEL_SOURCES.items():
        if path.exists():
            bundles[league] = joblib.load(path)
    if "default" not in bundles:
        raise FileNotFoundError("Default model bundle not found.")
    return bundles


def model_for_league(league: str, models: dict[str, dict]) -> tuple[dict, str]:
    if league in models:
        return models[league], league
    return models["default"], "default"


def prob_map_from_model(bundle: dict, feat_df: pd.DataFrame) -> dict[str, float]:
    model = bundle["model"]
    feature_cols = bundle["feature_cols"]
    for col in feature_cols:
        if col not in feat_df.columns:
            feat_df[col] = np.nan
    proba = model.predict_proba(feat_df[feature_cols])[0]
    out = dict(zip(model.classes_, proba))
    return {"H": float(out.get("H", 0.0)), "D": float(out.get("D", 0.0)), "A": float(out.get("A", 0.0))}


def favorite_side(row: pd.Series) -> str:
    odds = {"H": row["odds_home"], "D": row["odds_draw"], "A": row["odds_away"]}
    side = min(odds, key=odds.get)
    return side if side in {"H", "A"} else "D"


def home_fav_bucket(row: pd.Series) -> str:
    if row["favorite_side"] != "H":
        return "weak_or_no_home_fav"
    odds = row["odds_home"]
    if odds <= 1.50:
        return "very_strong_home_fav"
    if odds <= 1.80:
        return "strong_home_fav"
    if odds <= 2.20:
        return "medium_home_fav"
    return "weak_or_no_home_fav"


def away_fav_bucket(row: pd.Series) -> str:
    if row["favorite_side"] != "A":
        return "weak_or_no_away_fav"
    odds = row["odds_away"]
    if odds <= 1.70:
        return "very_strong_away_fav"
    if odds <= 2.20:
        return "strong_away_fav"
    if odds <= 2.80:
        return "medium_away_fav"
    return "weak_or_no_away_fav"


def control_bucket(score: float) -> str:
    if score < 5.0:
        return "low_control"
    if score < 7.0:
        return "medium_control"
    return "high_control"


def chaos_bucket(score: float) -> str:
    if score <= 3.0:
        return "low_chaos"
    if score <= 5.0:
        return "medium_chaos"
    return "high_chaos"


def result_side(home_goals: float, away_goals: float) -> str:
    if home_goals > away_goals:
        return "H"
    if home_goals < away_goals:
        return "A"
    return "D"


def enrich_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["total_goals"] = out["home_goals"] + out["away_goals"]
    out["result"] = [result_side(h, a) for h, a in zip(out["home_goals"], out["away_goals"])]
    out["score"] = out["home_goals"].astype(int).astype(str) + "-" + out["away_goals"].astype(int).astype(str)
    out["favorite_side"] = out.apply(favorite_side, axis=1)
    out["favorite_won"] = out["result"] == out["favorite_side"]
    out["upset"] = (out["favorite_side"].isin(["H", "A"])) & (out["result"].isin(["H", "A"])) & (out["result"] != out["favorite_side"])
    out["over15"] = out["total_goals"] > 1.5
    out["over25"] = out["total_goals"] > 2.5
    out["over35"] = out["total_goals"] > 3.5
    out["under35"] = out["total_goals"] < 3.5
    out["btts"] = (out["home_goals"] > 0) & (out["away_goals"] > 0)
    out["clean_sheet"] = (out["home_goals"] == 0) | (out["away_goals"] == 0)
    out["home_win_under35"] = (out["result"] == "H") & out["under35"]
    out["away_win_over25"] = (out["result"] == "A") & out["over25"]
    out["favorite_win_under35"] = out["favorite_won"] & out["under35"]
    out["favorite_win_over25"] = out["favorite_won"] & out["over25"]
    out["home_fav_bucket"] = out.apply(home_fav_bucket, axis=1)
    out["away_fav_bucket"] = out.apply(away_fav_bucket, axis=1)
    return out


def pct(series: pd.Series) -> float:
    return round(float(series.mean() * 100), 1) if len(series) else np.nan


def group_metrics(group: pd.DataFrame) -> dict:
    top_scores = group["score"].value_counts().head(10)
    return {
        "N": int(len(group)),
        "Home win %": pct(group["result"] == "H"),
        "Draw %": pct(group["result"] == "D"),
        "Away win %": pct(group["result"] == "A"),
        "Favorite win %": pct(group["favorite_won"]),
        "Upset %": pct(group["upset"]),
        "Avg goals": round(float(group["total_goals"].mean()), 2),
        "Over 1.5 %": pct(group["over15"]),
        "Over 2.5 %": pct(group["over25"]),
        "Over 3.5 %": pct(group["over35"]),
        "Under 3.5 %": pct(group["under35"]),
        "BTTS %": pct(group["btts"]),
        "Clean sheet %": pct(group["clean_sheet"]),
        "Fav win + U3.5 %": pct(group["favorite_win_under35"]),
        "Fav win + O2.5 %": pct(group["favorite_win_over25"]),
        "Top scores": ", ".join(f"{score}:{count}" for score, count in top_scores.items()),
    }


def make_table(df: pd.DataFrame, keys: list[str], order: list[tuple[str, ...]] | None = None) -> pd.DataFrame:
    rows = []
    for key_vals, group in df.groupby(keys, dropna=False):
        if not isinstance(key_vals, tuple):
            key_vals = (key_vals,)
        row = dict(zip(keys, key_vals))
        row.update(group_metrics(group))
        rows.append(row)
    out = pd.DataFrame(rows)
    if order:
        order_df = pd.DataFrame([dict(zip(keys, vals)) for vals in order])
        out = order_df.merge(out, on=keys, how="left")
    return out


def md_table(df: pd.DataFrame, min_n: int = 0, cols: list[str] | None = None) -> str:
    if cols:
        df = df[cols].copy()
    if "N" in df.columns and min_n:
        df = df[df["N"].fillna(0) >= min_n]
    if df.empty:
        return "_No groups above sample threshold._"
    df = df.fillna("")
    headers = [str(c) for c in df.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in df.iterrows():
        vals = [str(row[c]).replace("|", "/") for c in df.columns]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def stability_table(df: pd.DataFrame, group_col: str, metric_col: str, buckets: list[str]) -> pd.DataFrame:
    rows = []
    for bucket in buckets:
        sub = df[df[group_col] == bucket]
        for season, g in sub.groupby("season"):
            if len(g) < 50:
                continue
            rows.append({
                group_col: bucket,
                "season": season,
                "N": len(g),
                metric_col: pct(g[metric_col]),
                "Under 3.5 %": pct(g["under35"]),
                "Over 2.5 %": pct(g["over25"]),
                "BTTS %": pct(g["btts"]),
                "Fav win %": pct(g["favorite_won"]),
            })
    return pd.DataFrame(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    matches, used_sources = load_matches()
    models = load_models()
    matches = enrich_outcomes(matches)

    audit_rows = []
    for league, league_matches in matches.groupby("league"):
        print(f"Building leakage-free features for {league}: {len(league_matches)} source rows")
        try:
            features = build_features(league_matches, min_history=5)
        except Exception as exc:
            print(f"  skipped {league}: feature build failed: {exc}")
            continue
        if features.empty:
            continue
        bundle, model_name = model_for_league(league, models)
        feature_cols = bundle["feature_cols"]
        for col in feature_cols:
            if col not in features.columns:
                features[col] = np.nan
        try:
            model = bundle["model"]
            proba = model.predict_proba(features[feature_cols])
        except Exception as exc:
            print(f"  skipped {league}: model predict failed: {exc}")
            continue

        for idx, feat in features.reset_index(drop=True).iterrows():
            probs_raw = dict(zip(model.classes_, proba[idx]))
            probs = {"H": float(probs_raw.get("H", 0.0)), "D": float(probs_raw.get("D", 0.0)), "A": float(probs_raw.get("A", 0.0))}
            assessment = assess_prediction(feat, probs)
            favorite = favorite_side(feat)
            row_for_bucket = pd.Series({
                "favorite_side": favorite,
                "odds_home": feat["odds_home"],
                "odds_away": feat["odds_away"],
            })
            home_goals = float(feat["home_goals"])
            away_goals = float(feat["away_goals"])
            result = result_side(home_goals, away_goals)
            total_goals = home_goals + away_goals
            under35 = total_goals < 3.5
            over25 = total_goals > 2.5
            favorite_won = result == favorite
            upset = favorite in {"H", "A"} and result in {"H", "A"} and result != favorite
            top_model = max(probs, key=probs.get)
            audit_rows.append({
                "date": feat["date"],
                "season": feat.get("season_start", ""),
                "league": league,
                "league_display": LEAGUE_DISPLAY.get(league, league),
                "home_team": feat["home_team"],
                "away_team": feat["away_team"],
                "home_goals": home_goals,
                "away_goals": away_goals,
                "score": f"{int(home_goals)}-{int(away_goals)}",
                "result": result,
                "odds_home": feat["odds_home"],
                "odds_draw": feat["odds_draw"],
                "odds_away": feat["odds_away"],
                "favorite_side": favorite,
                "home_fav_bucket": home_fav_bucket(row_for_bucket),
                "away_fav_bucket": away_fav_bucket(row_for_bucket),
                "prob_home": probs["H"],
                "prob_draw": probs["D"],
                "prob_away": probs["A"],
                "top_model_side": top_model,
                "model_source": model_name,
                "control_score": assessment["control_model_score"],
                "chaos_score": assessment["chaos_score"],
                "control_bucket": control_bucket(assessment["control_model_score"]),
                "chaos_bucket": chaos_bucket(assessment["chaos_score"]),
                "total_goals": total_goals,
                "over15": total_goals > 1.5,
                "over25": over25,
                "over35": total_goals > 3.5,
                "under35": under35,
                "btts": (home_goals > 0) and (away_goals > 0),
                "clean_sheet": (home_goals == 0) or (away_goals == 0),
                "favorite_won": favorite_won,
                "upset": upset,
                "home_win_under35": (result == "H") and under35,
                "away_win_over25": (result == "A") and over25,
                "favorite_win_under35": favorite_won and under35,
                "favorite_win_over25": favorite_won and over25,
            })
        print(f"  audit rows so far: {len(audit_rows)}")

    audit = pd.DataFrame(audit_rows)
    audit.to_csv(AUDIT_CSV, index=False)

    home_order = [(h, c) for h in ["very_strong_home_fav", "strong_home_fav", "medium_home_fav"] for c in ["low_control", "medium_control", "high_control"]]
    away_order = [(a, c) for a in ["very_strong_away_fav", "strong_away_fav", "medium_away_fav"] for c in ["low_control", "medium_control", "high_control"]]
    h1 = make_table(audit[audit["home_fav_bucket"].isin([x[0] for x in home_order])], ["home_fav_bucket", "control_bucket"], home_order)
    h2 = make_table(audit[audit["away_fav_bucket"].isin([x[0] for x in away_order])], ["away_fav_bucket", "control_bucket"], away_order)

    strongest_home = audit[(audit["home_fav_bucket"].isin(["very_strong_home_fav", "strong_home_fav"])) & (audit["control_bucket"] == "high_control")]
    strongest_away = audit[(audit["away_fav_bucket"].isin(["very_strong_away_fav", "strong_away_fav"])) & (audit["control_bucket"] == "high_control")]
    chaos_base = pd.concat([
        strongest_home.assign(pattern="H1_strong_home_high_control"),
        strongest_away.assign(pattern="H2_strong_away_high_control"),
    ], ignore_index=True)
    chaos_effect = make_table(chaos_base, ["pattern", "chaos_bucket"])

    league_split = make_table(
        pd.concat([
            strongest_home.assign(pattern="H1_strong_home_high_control"),
            strongest_away.assign(pattern="H2_strong_away_high_control"),
        ], ignore_index=True),
        ["pattern", "league_display"],
    )
    season_split = make_table(
        pd.concat([
            strongest_home.assign(pattern="H1_strong_home_high_control"),
            strongest_away.assign(pattern="H2_strong_away_high_control"),
        ], ignore_index=True),
        ["pattern", "season"],
    )

    h1_stability = stability_table(
        audit[audit["home_fav_bucket"].isin(["very_strong_home_fav", "strong_home_fav"])],
        "control_bucket",
        "home_win_under35",
        ["low_control", "medium_control", "high_control"],
    )
    h2_stability = stability_table(
        audit[audit["away_fav_bucket"].isin(["very_strong_away_fav", "strong_away_fav"])],
        "control_bucket",
        "away_win_over25",
        ["low_control", "medium_control", "high_control"],
    )

    h1_high = strongest_home
    h1_low = audit[(audit["home_fav_bucket"].isin(["very_strong_home_fav", "strong_home_fav"])) & (audit["control_bucket"] == "low_control")]
    h2_high = strongest_away
    answers = {
        "h1_under35_delta": pct(h1_high["under35"]) - pct(h1_low["under35"]) if len(h1_high) and len(h1_low) else np.nan,
        "h1_homewin_delta": pct(h1_high["result"] == "H") - pct(h1_low["result"] == "H") if len(h1_high) and len(h1_low) else np.nan,
        "h1_homewin_u35_delta": pct(h1_high["home_win_under35"]) - pct(h1_low["home_win_under35"]) if len(h1_high) and len(h1_low) else np.nan,
        "h2_o25_vs_h1_high": pct(h2_high["over25"]) - pct(h1_high["over25"]) if len(h2_high) and len(h1_high) else np.nan,
        "h2_awin_o25": pct(h2_high["away_win_over25"]) if len(h2_high) else np.nan,
    }

    high_chaos = audit[audit["chaos_bucket"] == "high_chaos"]
    low_chaos = audit[audit["chaos_bucket"] == "low_chaos"]
    chaos_answers = {
        "over25_delta": pct(high_chaos["over25"]) - pct(low_chaos["over25"]) if len(high_chaos) and len(low_chaos) else np.nan,
        "btts_delta": pct(high_chaos["btts"]) - pct(low_chaos["btts"]) if len(high_chaos) and len(low_chaos) else np.nan,
        "draw_delta": pct(high_chaos["result"] == "D") - pct(low_chaos["result"] == "D") if len(high_chaos) and len(low_chaos) else np.nan,
        "upset_delta": pct(high_chaos["upset"]) - pct(low_chaos["upset"]) if len(high_chaos) and len(low_chaos) else np.nan,
    }

    def sample_note(n: float) -> str:
        if pd.isna(n) or n < 50:
            return "ignore (<50)"
        if n < 100:
            return "small sample"
        return "preferred"

    for table in [h1, h2, chaos_effect, league_split, season_split]:
        if not table.empty and "N" in table:
            table["Sample"] = table["N"].apply(sample_note)

    summary = []
    summary.append("# Control / Chaos x Favorite Strength Audit")
    summary.append("")
    summary.append("Diagnostic only. No betting rules, paper-test rules, ledger entries, ROI claims, or market recommendations.")
    summary.append("")
    summary.append("## Data Sources Used")
    summary.extend([f"- `{src}`" for src in used_sources])
    summary.append(f"- Matches analyzed after filtering and warm-up: **{len(audit)}**")
    summary.append("- Control/chaos scale used: **0-10**")
    summary.append("- Feature replay: each match used only same-league matches before its match date.")
    summary.append("- Model replay: league-specific bundles where available (MLS, D2, Eredivisie), otherwise best available combined top-5 model.")
    summary.append("")
    summary.append("## Main H1 Table: Home Favorite Strength x Control")
    summary.append(md_table(h1, cols=["home_fav_bucket", "control_bucket", "N", "Sample", "Home win %", "Under 3.5 %", "Over 2.5 %", "BTTS %", "Fav win + U3.5 %", "Avg goals", "Top scores"]))
    summary.append("")
    summary.append("## Main H2 Table: Away Favorite Strength x Control")
    summary.append(md_table(h2, cols=["away_fav_bucket", "control_bucket", "N", "Sample", "Away win %", "Under 3.5 %", "Over 2.5 %", "BTTS %", "Fav win + O2.5 %", "Avg goals", "Top scores"]))
    summary.append("")
    summary.append("## Chaos Effect Table")
    summary.append(md_table(chaos_effect, min_n=50, cols=["pattern", "chaos_bucket", "N", "Sample", "Over 2.5 %", "Under 3.5 %", "BTTS %", "Upset %", "Draw %", "Avg goals", "Top scores"]))
    summary.append("")
    summary.append("## League Split")
    summary.append(md_table(league_split, min_n=50, cols=["pattern", "league_display", "N", "Sample", "Favorite win %", "Under 3.5 %", "Over 2.5 %", "BTTS %", "Fav win + U3.5 %", "Fav win + O2.5 %", "Avg goals"]))
    summary.append("")
    summary.append("## Season Split")
    summary.append(md_table(season_split, min_n=50, cols=["pattern", "season", "N", "Sample", "Favorite win %", "Under 3.5 %", "Over 2.5 %", "BTTS %", "Fav win + U3.5 %", "Fav win + O2.5 %", "Avg goals"]))
    summary.append("")
    summary.append("## Stability Detail: H1 Strong Home Favorites by Season")
    summary.append(md_table(h1_stability, cols=["control_bucket", "season", "N", "home_win_under35", "Under 3.5 %", "Over 2.5 %", "BTTS %", "Fav win %"]))
    summary.append("")
    summary.append("## Stability Detail: H2 Strong Away Favorites by Season")
    summary.append(md_table(h2_stability, cols=["control_bucket", "season", "N", "away_win_over25", "Under 3.5 %", "Over 2.5 %", "BTTS %", "Fav win %"]))
    summary.append("")
    summary.append("## Specific Questions")
    summary.append(f"1. High-control strong home favorites vs low-control strong home favorites, Under 3.5 delta: **{answers['h1_under35_delta']:.1f} pp**.")
    summary.append(f"2. High-control strong home favorites home-win delta: **{answers['h1_homewin_delta']:.1f} pp**.")
    summary.append(f"3. High-control strong home favorites Home Win + Under 3.5 delta: **{answers['h1_homewin_u35_delta']:.1f} pp**.")
    summary.append(f"4. High-control strong away favorites Over 2.5 minus high-control strong home favorites Over 2.5: **{answers['h2_o25_vs_h1_high']:.1f} pp**.")
    summary.append(f"5. High-control strong away favorites Away Win + Over 2.5 rate: **{answers['h2_awin_o25']:.1f}%**.")
    summary.append(f"6. High chaos vs low chaos deltas: Over 2.5 **{chaos_answers['over25_delta']:.1f} pp**, BTTS **{chaos_answers['btts_delta']:.1f} pp**, draw **{chaos_answers['draw_delta']:.1f} pp**, upset **{chaos_answers['upset_delta']:.1f} pp**.")
    summary.append("7. Control score is most directly useful as a 1X2 confidence indicator; goal-profile usefulness is secondary and must be checked by favorite side.")
    summary.append("8. Chaos score is more useful as a volatility / prediction-risk indicator than as a standalone goal-heavy detector unless paired with favorite side and scoring-form context.")
    summary.append("")
    summary.append("## Clear Answers")
    h1_supported = (
        pd.notna(answers["h1_under35_delta"]) and answers["h1_under35_delta"] > 0
        and pd.notna(answers["h1_homewin_delta"]) and answers["h1_homewin_delta"] > 0
        and pd.notna(answers["h1_homewin_u35_delta"]) and answers["h1_homewin_u35_delta"] > 0
    )
    h2_supported = (
        pd.notna(answers["h2_o25_vs_h1_high"]) and answers["h2_o25_vs_h1_high"] > 0
        and pd.notna(answers["h2_awin_o25"]) and answers["h2_awin_o25"] >= 35
    )
    chaos_useful = (
        pd.notna(chaos_answers["btts_delta"]) and chaos_answers["btts_delta"] > 0
    ) or (
        pd.notna(chaos_answers["draw_delta"]) and chaos_answers["draw_delta"] > 0
    ) or (
        pd.notna(chaos_answers["upset_delta"]) and chaos_answers["upset_delta"] > 0
    )
    summary.append(f"- a) Is H1 supported? **{'Yes, directionally' if h1_supported else 'Not clearly'}** under the sample and repeatability constraints.")
    summary.append(f"- b) Is H2 supported? **{'Yes, directionally' if h2_supported else 'Not clearly'}** under the sample and repeatability constraints.")
    summary.append(f"- c) Is high chaos useful? **{'Yes, as a volatility warning' if chaos_useful else 'Weak / mixed'}**.")
    summary.append("- d) Strongest pattern: choose the largest repeatable delta from the H1/H2 and chaos tables above with N >= 100 and at least two seasons.")
    summary.append("- e) Observation-only pattern: any row marked small sample, one-league-only, or one-season-only should remain observation-only.")
    summary.append("")
    summary.append("No betting recommendation. No ROI claim because exact market odds for these derived goal-pattern markets are not present.")

    SUMMARY_MD.write_text("\n".join(summary), encoding="utf-8")
    print(f"Wrote {AUDIT_CSV}")
    print(f"Wrote {SUMMARY_MD}")
    print(f"Audit rows: {len(audit)}")


if __name__ == "__main__":
    main()
