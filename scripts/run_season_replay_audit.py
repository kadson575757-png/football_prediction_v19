# -*- coding: utf-8 -*-
"""Season-by-season and matchday-by-matchday replay audit.

Replays a full historical season for a given league, simulating pre-match
diagnostic reports with strict no-future-leakage and evaluating them against
actual results.

This is a DIAGNOSTIC / RESEARCH tool only.
- No betting rules.
- No paper-test rules.
- No ledger entries.
- No ROI optimisation.

Modes
-----
diagnostic_replay
    Build pre-match features from rolling form statistics and market odds alone.
    No ML model is trained or loaded. Probabilities come from de-vigged odds
    when available, and from a simple form-weighted estimator otherwise.

walk_forward  (TRUE ML WALK-FORWARD)
    For every matchday/date group in the target season:
      1. cutoff_date  = earliest date in the group
      2. train_df     = all matches with date < cutoff_date  (strict, no leakage)
      3. A scikit-learn model is trained on train_df features
      4. The model predicts H/D/A probabilities for each match in the group
      5. likely_1x2 and confidence are derived from those ML probabilities
      6. control_score and chaos_score are still derived from rolling form stats
      7. recommended_market_type/subtype are generated as normal from the above

    The model is NEVER trained on current or future matches.
    A pre-trained full-season model is NEVER used.

    --retrain-frequency matchday  (default) trains a fresh model per cutoff group.
    --retrain-frequency season    trains exactly once (first eligible cutoff) and
                                  reuses that model for the rest of the season.

Usage
-----
    python scripts/run_season_replay_audit.py \\
        --league Eredivisie --season 2024 \\
        --mode diagnostic_replay \\
        --output-dir outputs/season_replay

    python scripts/run_season_replay_audit.py \\
        --league "La Liga" --season 2023 \\
        --mode walk_forward \\
        --min-warmup-matches 60
"""
from __future__ import annotations

import argparse
import math
import sys
import textwrap
import warnings
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.diagnostics import build_recommended_market  # noqa: E402
from football_prediction_v19.diagnostics import apply_league_market_profile  # noqa: E402
from football_prediction_v19.diagnostics import build_market_tier  # noqa: E402
from football_prediction_v19.features import (          # noqa: E402
    build_features as _build_features,
    build_fixture_features as _build_fixture_features,
    build_extended_features,
)
from football_prediction_v19.model import (             # noqa: E402
    build_pipeline as _build_pipeline,
    _align_proba,
    CLASS_ORDER,
)
from football_prediction_v19.data import (              # noqa: E402
    feature_columns as _feature_columns,
)

# ---------------------------------------------------------------------------
# League / division mappings
# ---------------------------------------------------------------------------

LEAGUE_TO_CODE: dict[str, str] = {
    "Premier League": "E0",  "EPL": "E0",  "E0": "E0",
    "Serie A": "I1",         "I1": "I1",
    "La Liga": "SP1",        "SP1": "SP1",
    "Bundesliga": "D1",      "D1": "D1",
    "Ligue 1": "F1",         "F1": "F1",
    "Eredivisie": "N1",      "N1": "N1",
    "2. Bundesliga": "D2",   "D2": "D2",
    "MLS": "MLS",
    # Belgian Pro League
    "Belgian Pro League": "B1",  "Jupiler Pro League": "B1",
    "Belgium": "B1",             "B1": "B1",
    # Brazilian Série A
    "Brasileiro Serie A": "BRA",
    "Campeonato Brasileiro Serie A": "BRA",
    "Brasileiro": "BRA",
    "Brazil": "BRA",             "BRA": "BRA",
}

CODE_TO_LEAGUE: dict[str, str] = {
    "E0": "Premier League", "I1": "Serie A",  "SP1": "La Liga",
    "D1": "Bundesliga",     "F1": "Ligue 1",  "N1": "Eredivisie",
    "D2": "2. Bundesliga",  "MLS": "MLS",
    "B1": "Belgian Pro League",
    "BRA": "Brasileiro Serie A",
}

GOAL_LEAGUES: frozenset[str] = frozenset({"Eredivisie", "N1"})

_SMALL_SAMPLE_THRESHOLD = 5   # fewer prior games → data_warning=True
_ROLLING_N = 10               # rolling window for team stats


# ---------------------------------------------------------------------------
# Leakage-safety assertion
# ---------------------------------------------------------------------------

def _assert_no_leakage(
    prior_df: pd.DataFrame,
    cutoff_date: pd.Timestamp,
    label: str = "",
) -> None:
    """Assert that *prior_df* contains NO rows with date >= *cutoff_date*.

    This is a hard integrity check: any violation means future match data has
    contaminated the training/feature window, which would invalidate all
    diagnostic results produced from those features.

    Parameters
    ----------
    prior_df    : DataFrame that must contain only past matches.
    cutoff_date : The earliest date of the current matchday (exclusive upper bound).
    label       : Optional context string for the error message.

    Raises
    ------
    AssertionError
        If ``prior_df`` is non-empty AND its maximum date is >= ``cutoff_date``,
        or if any individual row has date >= ``cutoff_date``.
    """
    if prior_df.empty:
        return
    max_date = prior_df["date"].max()
    ctx = f" [{label}]" if label else ""
    assert max_date < cutoff_date, (
        f"Leakage detected{ctx}: prior_df max date "
        f"{max_date} >= cutoff {cutoff_date}"
    )
    leaked_count = int((prior_df["date"] >= cutoff_date).sum())
    assert leaked_count == 0, (
        f"Leakage detected{ctx}: {leaked_count} row(s) in prior_df "
        f"have date >= cutoff {cutoff_date}"
    )

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--league", required=True,
                   help="League name or code (e.g. 'Eredivisie', 'N1', 'La Liga', 'SP1')")
    p.add_argument("--season", required=True,
                   help="Season year (e.g. 2024, 2023)")
    p.add_argument("--mode", choices=["diagnostic_replay", "walk_forward"],
                   default="diagnostic_replay",
                   help="Replay mode (default: diagnostic_replay)")
    p.add_argument("--history", default=None,
                   help="Optional path to a pre-built history CSV. "
                        "If omitted, the standard data/raw/ file is used.")
    p.add_argument("--output-dir", default=str(ROOT / "outputs" / "season_replay"),
                   help="Directory to write output files (default: outputs/season_replay)")
    p.add_argument("--min-warmup-matches", type=int, default=50,
                   help="Skip matchdays until this many prior matches exist (default: 50)")
    p.add_argument("--retrain-frequency",
                   choices=["matchday", "season"],
                   default="matchday",
                   help="walk_forward only — how often to retrain the ML model. "
                        "'matchday' trains a fresh model at every cutoff (default). "
                        "'season' trains once at the first eligible cutoff and reuses it.")
    p.add_argument("--wf-model",
                   choices=["logistic_regression", "random_forest", "gradient_boosting"],
                   default="logistic_regression",
                   help="walk_forward only — sklearn classifier to use (default: logistic_regression)")
    return p


# ---------------------------------------------------------------------------
# Data loading and normalisation
# ---------------------------------------------------------------------------

def resolve_league(league_arg: str) -> tuple[str, str]:
    """Return (div_code, league_name) or raise ValueError."""
    code = LEAGUE_TO_CODE.get(league_arg)
    if code is None:
        raise ValueError(
            f"Unknown league: {league_arg!r}.\n"
            f"Supported: {sorted(LEAGUE_TO_CODE.keys())}"
        )
    return code, CODE_TO_LEAGUE.get(code, league_arg)


def find_data_file(div_code: str, season: str, history_file: Optional[str]) -> Path:
    """Locate the raw CSV for this league/season."""
    if history_file:
        p = Path(history_file)
        if not p.exists():
            raise FileNotFoundError(f"History file not found: {p}")
        return p

    raw_dir = ROOT / "data" / "raw"
    candidate = raw_dir / f"football_data_{div_code}_{season}.csv"
    if candidate.exists():
        return candidate

    # Try adjacent seasons (user might pass e.g. "2023-24" as "2023")
    for suffix in ["", "-24", "-23", "-22"]:
        alt = raw_dir / f"football_data_{div_code}_{season}{suffix}.csv"
        if alt.exists():
            return alt

    raise FileNotFoundError(
        f"No data file found for {div_code} season {season}.\n"
        f"Expected: {candidate}\n"
        f"Available files:\n"
        + "\n".join(f"  {f.name}" for f in sorted(raw_dir.glob(f"football_data_{div_code}_*.csv")))
    )


def _pick_odds(row: pd.Series, primary: str, fallback: str) -> Optional[float]:
    v = row.get(primary)
    if pd.notna(v) and float(v) > 1.0:
        return float(v)
    v = row.get(fallback)
    if pd.notna(v) and float(v) > 1.0:
        return float(v)
    return None


def normalise_raw(df: pd.DataFrame, div_code: str, season: str) -> pd.DataFrame:
    """Normalise a football-data.org CSV to the canonical project schema."""
    out = pd.DataFrame()
    out["div"]        = df.get("Div", div_code)
    out["league"]     = CODE_TO_LEAGUE.get(div_code, div_code)
    out["season"]     = season

    # Date — football-data.org uses DD/MM/YYYY
    out["date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")

    out["home_team"]  = df["HomeTeam"].astype(str).str.strip()
    out["away_team"]  = df["AwayTeam"].astype(str).str.strip()

    # Goals — drop rows where goals are missing (future fixtures)
    out["home_goals"] = pd.to_numeric(df.get("FTHG", df.get("HG")), errors="coerce")
    out["away_goals"] = pd.to_numeric(df.get("FTAG", df.get("AG")), errors="coerce")
    out["ftr"]        = df.get("FTR", "")

    # Odds — prefer B365, fall back to Avg
    out["odds_home"] = df.apply(lambda r: _pick_odds(r, "B365H", "AvgH"), axis=1)
    out["odds_draw"] = df.apply(lambda r: _pick_odds(r, "B365D", "AvgD"), axis=1)
    out["odds_away"] = df.apply(lambda r: _pick_odds(r, "B365A", "AvgA"), axis=1)

    # Matchday — use if present, else will be derived from date groups
    if "Wk" in df.columns:
        out["matchday"] = pd.to_numeric(df["Wk"], errors="coerce")
    elif "Round" in df.columns:
        out["matchday"] = pd.to_numeric(df["Round"].astype(str).str.extract(r"(\d+)")[0],
                                         errors="coerce")
    # else: no matchday column → group_by_matchday will use date

    # Drop rows with no date or no goals (future fixtures in partial files)
    out = out[out["date"].notna() & out["home_goals"].notna() & out["away_goals"].notna()]
    out = out.sort_values("date").reset_index(drop=True)
    return out


def load_league_data(league_arg: str, season: str, history_file: Optional[str]) -> pd.DataFrame:
    div_code, _league_name = resolve_league(league_arg)
    path = find_data_file(div_code, season, history_file)
    try:
        df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    except Exception as exc:
        raise RuntimeError(f"Failed to read {path}: {exc}") from exc
    return normalise_raw(df, div_code, season)


# ---------------------------------------------------------------------------
# Matchday grouping
# ---------------------------------------------------------------------------

def group_by_matchday(df: pd.DataFrame) -> list[tuple[Any, pd.DataFrame]]:
    """Return ordered list of (matchday_label, group_df) with no future leakage.

    If the DataFrame has a numeric 'matchday' column, groups are by matchday.
    Otherwise each unique date forms its own group (sorted chronologically).
    """
    if "matchday" in df.columns and df["matchday"].notna().any():
        groups = []
        for md, grp in df.groupby("matchday", sort=True):
            groups.append((md, grp.reset_index(drop=True)))
        return groups
    else:
        groups = []
        for dt, grp in df.groupby("date", sort=True):
            groups.append((dt, grp.reset_index(drop=True)))
        return groups


# ---------------------------------------------------------------------------
# Rolling team statistics (no future leakage)
# ---------------------------------------------------------------------------

def team_rolling_stats(team: str, prior_df: pd.DataFrame, n: int = _ROLLING_N) -> dict:
    """Compute rolling statistics for *team* using only prior_df matches.

    prior_df must contain only matches played BEFORE the current matchday —
    this is the caller's responsibility to enforce.
    """
    home_m = prior_df[prior_df["home_team"] == team].copy()
    away_m = prior_df[prior_df["away_team"] == team].copy()

    # Build team-perspective view
    home_m["gf"] = home_m["home_goals"]
    home_m["ga"] = home_m["away_goals"]
    away_m["gf"] = away_m["away_goals"]
    away_m["ga"] = away_m["home_goals"]

    def _pts(gf_col, ga_col, df_):
        return (
            (df_[gf_col] > df_[ga_col]).astype(int) * 3
            + (df_[gf_col] == df_[ga_col]).astype(int)
        )

    home_m["pts"] = _pts("home_goals", "away_goals", home_m)
    away_m["pts"] = _pts("away_goals", "home_goals", away_m)

    cols = ["date", "gf", "ga", "pts"]
    combined = pd.concat(
        [home_m[cols], away_m[cols]], ignore_index=True
    ).sort_values("date").tail(n)

    if len(combined) == 0:
        return {
            "n_games": 0,
            "points_per_game": 1.5,
            "avg_gf": 1.2,
            "avg_ga": 1.2,
            "over25_rate": 0.50,
            "btts_rate": 0.40,
            "draw_rate": 0.25,
            "win_rate": 0.33,
        }

    total = combined["gf"] + combined["ga"]
    return {
        "n_games":         len(combined),
        "points_per_game": float(combined["pts"].mean()),
        "avg_gf":          float(combined["gf"].mean()),
        "avg_ga":          float(combined["ga"].mean()),
        "over25_rate":     float((total > 2.5).mean()),
        "btts_rate":       float(((combined["gf"] > 0) & (combined["ga"] > 0)).mean()),
        "draw_rate":       float((combined["pts"] == 1).mean()),
        "win_rate":        float((combined["pts"] == 3).mean()),
    }


# ---------------------------------------------------------------------------
# Control / chaos scoring from form + odds
# ---------------------------------------------------------------------------

def _devig_probs(oh: float, od: float, oa: float) -> dict[str, float]:
    """Remove bookmaker margin and return fair probabilities."""
    inv_h, inv_d, inv_a = 1 / oh, 1 / od, 1 / oa
    total = inv_h + inv_d + inv_a
    return {"home": inv_h / total, "draw": inv_d / total, "away": inv_a / total}


def compute_control_score(
    home_stats: dict, away_stats: dict,
    odds_home: Optional[float], odds_draw: Optional[float], odds_away: Optional[float],
) -> float:
    """Return control score 0-10.  High = clear direction, consistent form."""
    # Form gap: PPG difference normalised (0-3 scale → 0-1)
    ppg_gap = min(abs(home_stats["points_per_game"] - away_stats["points_per_game"]) / 3.0, 1.0)

    # Odds clarity: lower min odds → clearer favourite → more control
    if odds_home and odds_draw and odds_away and odds_home > 1 and odds_away > 1:
        min_odds = min(odds_home, odds_away)
        # odds 1.0 → 1.0 clarity; odds 4.0 → 0.0
        odds_clarity = max(0.0, min(1.0, (4.0 - min_odds) / 3.0))
    else:
        odds_clarity = 0.30

    # Data sufficiency: penalise low sample sizes
    data_ok = home_stats["n_games"] >= _SMALL_SAMPLE_THRESHOLD and \
              away_stats["n_games"] >= _SMALL_SAMPLE_THRESHOLD
    multiplier = 1.0 if data_ok else 0.5

    raw = (ppg_gap * 3 + odds_clarity * 7) * multiplier
    return round(max(0.0, min(10.0, raw)), 2)


def compute_chaos_score(
    home_stats: dict, away_stats: dict,
    odds_draw: Optional[float],
) -> float:
    """Return chaos score 0-10.  High = volatile, high-scoring, draw-prone."""
    combined_over25 = (home_stats["over25_rate"] + away_stats["over25_rate"]) / 2
    combined_btts   = (home_stats["btts_rate"]   + away_stats["btts_rate"])   / 2
    combined_draw   = (home_stats["draw_rate"]   + away_stats["draw_rate"])   / 2

    # Draw market: tight draw odds signal unpredictability
    draw_market = 0.0
    if odds_draw and odds_draw > 1:
        draw_market = max(0.0, (4.0 - odds_draw) / 4.0)  # 1.0 at odds 1.0; 0 at odds 4+

    raw = combined_over25 * 3.5 + combined_btts * 3.0 + combined_draw * 2.0 + draw_market * 1.5
    return round(max(0.0, min(10.0, raw)), 2)


# ---------------------------------------------------------------------------
# Probability estimation
# ---------------------------------------------------------------------------

def estimate_probabilities(
    home_stats: dict, away_stats: dict,
    odds_home: Optional[float], odds_draw: Optional[float], odds_away: Optional[float],
) -> dict[str, float]:
    """De-vig odds when available; fall back to form-weighted estimate."""
    if (odds_home and odds_draw and odds_away
            and odds_home > 1 and odds_draw > 1 and odds_away > 1):
        return _devig_probs(odds_home, odds_draw, odds_away)

    # Form-based fallback: map PPG to rough win probability
    # Home advantage ~0.3 PPG equivalent
    HOME_ADV = 0.3
    h = home_stats["points_per_game"] + HOME_ADV
    a = away_stats["points_per_game"]
    total_form = h + a
    if total_form <= 0:
        return {"home": 0.40, "draw": 0.28, "away": 0.32}

    raw_home = h / (total_form + 1)  # +1 dampens extremes
    raw_away = a / (total_form + 1)
    raw_draw = 1 - raw_home - raw_away

    # Clamp
    raw_home = max(0.05, min(0.80, raw_home))
    raw_away = max(0.05, min(0.80, raw_away))
    raw_draw = max(0.10, min(0.45, raw_draw))
    total = raw_home + raw_draw + raw_away
    return {
        "home": round(raw_home / total, 4),
        "draw": round(raw_draw / total, 4),
        "away": round(raw_away / total, 4),
    }


def determine_likely_1x2(probs: dict[str, float]) -> str:
    if probs["home"] >= probs["draw"] and probs["home"] >= probs["away"]:
        return "Home"
    if probs["away"] >= probs["home"] and probs["away"] >= probs["draw"]:
        return "Away"
    return "Draw"


def determine_confidence(top_prob: float, control: float) -> str:
    if top_prob >= 0.58 and control >= 7.0:
        return "HIGH"
    if top_prob >= 0.50 and control >= 4.0:
        return "MEDIUM"
    if top_prob < 0.38 or control < 1.5:
        return "NO-CONFIDENCE"
    return "LOW"


# ---------------------------------------------------------------------------
# Match feature building (no future leakage — prior_df is caller's responsibility)
# ---------------------------------------------------------------------------

def build_match_features(
    match: pd.Series,
    prior_df: pd.DataFrame,
    mode: str,
    league_name: str,
) -> dict[str, Any]:
    """Build the feature dict for a single pre-match prediction row.

    prior_df MUST contain only matches played BEFORE the current match's
    matchday. Future leakage is the caller's responsibility to prevent.
    """
    home = str(match["home_team"])
    away = str(match["away_team"])

    hs = team_rolling_stats(home, prior_df)
    as_ = team_rolling_stats(away, prior_df)

    oh = match.get("odds_home") if pd.notna(match.get("odds_home", float("nan"))) else None
    od = match.get("odds_draw") if pd.notna(match.get("odds_draw", float("nan"))) else None
    oa = match.get("odds_away") if pd.notna(match.get("odds_away", float("nan"))) else None

    control = compute_control_score(hs, as_, oh, od, oa)
    chaos   = compute_chaos_score(hs, as_, od)
    probs   = estimate_probabilities(hs, as_, oh, od, oa)
    likely  = determine_likely_1x2(probs)
    top_prob = max(probs.values())
    confidence = determine_confidence(top_prob, control)

    # Goal market signals
    comb_over25 = (hs["over25_rate"] + as_["over25_rate"]) / 2
    comb_btts   = (hs["btts_rate"]   + as_["btts_rate"])   / 2

    over25_signal = (
        "OVER likely"   if comb_over25 > 0.60
        else "UNDER likely" if comb_over25 < 0.35
        else "unclear"
    )
    btts_signal = (
        "BTTS YES likely" if comb_btts > 0.55
        else "BTTS NO likely" if comb_btts < 0.30
        else "unclear"
    )

    both_over = hs["over25_rate"] > 0.60 and as_["over25_rate"] > 0.60
    both_btts  = hs["btts_rate"]  > 0.55 and as_["btts_rate"]  > 0.55

    data_warning = (
        hs["n_games"] < _SMALL_SAMPLE_THRESHOLD
        or as_["n_games"] < _SMALL_SAMPLE_THRESHOLD
    )

    return {
        "league":              league_name,
        "season":              str(match.get("season", "")),
        "date":                str(match["date"])[:10],
        "home_team":           home,
        "away_team":           away,
        "odds_home":           oh,
        "odds_draw":           od,
        "odds_away":           oa,
        "control_score_10":    control,
        "chaos_score_10":      chaos,
        "likely_1x2":          likely,
        "confidence":          confidence,
        "model_home_prob":     probs["home"],
        "model_draw_prob":     probs["draw"],
        "model_away_prob":     probs["away"],
        "over25_signal":       over25_signal,
        "btts_signal":         btts_signal,
        "both_over":           both_over,
        "both_btts":           both_btts,
        "data_warning":        data_warning,
        "probability_profile": "",        # filled by control_chaos_profile downstream
        "home_stats_n":        hs["n_games"],
        "away_stats_n":        as_["n_games"],
        "home_ppg":            round(hs["points_per_game"], 3),
        "away_ppg":            round(as_["points_per_game"], 3),
        "home_over25_rate":    round(hs["over25_rate"], 3),
        "away_over25_rate":    round(as_["over25_rate"], 3),
        "home_btts_rate":      round(hs["btts_rate"], 3),
        "away_btts_rate":      round(as_["btts_rate"], 3),
        "mode":                mode,
    }


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------

def _actual_actuals(hg: float, ag: float) -> dict[str, Any]:
    total = hg + ag
    result = "H" if hg > ag else ("A" if ag > hg else "D")
    return {
        "actual_result":      result,
        "actual_home_goals":  hg,
        "actual_away_goals":  ag,
        "actual_total_goals": total,
        "actual_over25":      int(total > 2.5),
        "actual_under25":     int(total < 2.5),
        "actual_under35":     int(total < 3.5),
        "actual_btts":        int(hg > 0 and ag > 0),
    }


def evaluate_type_success(pred: dict[str, Any]) -> Optional[bool]:
    """Evaluate recommended_market_type success using the canonical OR/AND rules."""
    mtype = str(pred.get("recommended_market_type", ""))
    hg = pred.get("actual_home_goals")
    ag = pred.get("actual_away_goals")
    if hg is None or ag is None or math.isnan(float(hg)) or math.isnan(float(ag)):
        return None

    hg, ag = float(hg), float(ag)
    total = hg + ag
    result = pred.get("actual_result", "")
    read   = str(pred.get("recommended_market_read", "")).lower()
    likely = str(pred.get("likely_1x2", ""))
    conf   = str(pred.get("confidence", "")).upper()

    if mtype == "BTTS_OVER":
        return (total > 2.5) or (hg > 0 and ag > 0)

    if mtype == "UNDER":
        return total < 3.5

    if mtype == "DIRECTION":
        if "home" in read: return result == "H"
        if "away" in read: return result == "A"
        if "draw" in read: return result == "D"
        return result == likely[0] if likely else None

    if mtype == "DOUBLE_CHANCE":
        if "1x" in read or "home_or_draw" in read: return result in {"H", "D"}
        if "x2" in read or "away_or_draw" in read: return result in {"A", "D"}
        if likely == "Home": return result in {"H", "D"}
        if likely == "Away": return result in {"A", "D"}
        return None

    if mtype == "AVOID":
        # AVOID success = the match was indeed hard to predict
        direction_wrong = (result != likely[0]) if likely else False
        high_goals = total >= 4
        is_draw    = result == "D"
        no_conf    = conf == "NO-CONFIDENCE"
        return direction_wrong or high_goals or is_draw or no_conf

    return None  # OBSERVE_ONLY or unknown


def evaluate_subtype_success(pred: dict[str, Any]) -> Optional[bool]:
    """Evaluate recommended_market_subtype with per-subtype precise rules."""
    subtype = str(pred.get("recommended_market_subtype", "")).upper().strip()
    hg = pred.get("actual_home_goals")
    ag = pred.get("actual_away_goals")

    if subtype in ("NONE", "AVOID_VOLATILE", "AVOID_LOW_CONTROL", "OBSERVE_DATA_WARNING", ""):
        return None
    if hg is None or ag is None or math.isnan(float(hg)) or math.isnan(float(ag)):
        return None

    hg, ag = float(hg), float(ag)
    total  = hg + ag
    result = "H" if hg > ag else ("A" if ag > hg else "D")

    if subtype == "OVER_25":         return total > 2.5
    if subtype == "BTTS":            return hg > 0 and ag > 0
    if subtype == "BOTH_OVER25_BTTS": return (total > 2.5) and (hg > 0 and ag > 0)
    if subtype == "UNDER_25":        return total < 2.5
    if subtype == "UNDER_35":        return total < 3.5
    if subtype == "DIRECTION_HOME":  return result == "H"
    if subtype == "DIRECTION_AWAY":  return result == "A"
    if subtype == "DOUBLE_CHANCE_1X": return result in ("H", "D")
    if subtype == "DOUBLE_CHANCE_X2": return result in ("A", "D")
    return None


# ---------------------------------------------------------------------------
# Dimension helpers
# ---------------------------------------------------------------------------

def _odds_bucket(oh: Optional[float], oa: Optional[float]) -> str:
    if oh is None or oa is None:
        return "no_odds"
    best = min(oh, oa)
    if best <= 1.5:  return "heavy_fav (<=1.5)"
    if best <= 2.0:  return "strong_fav (1.5-2.0)"
    if best <= 2.5:  return "medium_fav (2.0-2.5)"
    return "no_clear_fav (>2.5)"


def _ctrl_bucket(c: float) -> str:
    if c >= 7.0: return "high (7-10)"
    if c >= 5.0: return "medium (5-7)"
    if c >= 3.0: return "low (3-5)"
    return "very_low (<3)"


def _chaos_bucket(c: float) -> str:
    if c >= 6.0: return "high (6-10)"
    if c >= 4.0: return "medium (4-6)"
    return "low (<4)"


def _season_phase(match_rank: int, total_matches: int) -> str:
    third = total_matches / 3
    if match_rank <= third:       return "early"
    if match_rank <= 2 * third:   return "mid"
    return "late"


def _fav_side(oh: Optional[float], oa: Optional[float], od: Optional[float]) -> str:
    if not (oh and oa and od and oh > 1 and oa > 1 and od > 1):
        return "no_odds"
    mn = min(oh, oa, od)
    if [oh, oa, od].count(mn) > 1:
        return "NO_CLEAR_FAVORITE"
    if oh == mn: return "HOME_FAVORITE"
    if oa == mn: return "AWAY_FAVORITE"
    return "NO_CLEAR_FAVORITE"


# ---------------------------------------------------------------------------
# True walk-forward ML helpers
# ---------------------------------------------------------------------------

def _prepare_for_ml(df: pd.DataFrame) -> pd.DataFrame:
    """Convert normalise_raw output to a format accepted by build_features.

    build_features → clean_matches requires a 'score' column (e.g. '2-1')
    and optional xg/venue/referee columns.  normalise_raw gives us home_goals
    and away_goals as numerics, so we synthesise the rest here.

    The returned DataFrame is used ONLY for ML feature building; it is never
    used for evaluation (goals columns remain present for clean_matches to pick
    up as the target).
    """
    out = df.copy()
    # Synthesise 'score' string that clean_matches can parse
    def _make_score(row: pd.Series) -> object:
        if pd.notna(row["home_goals"]) and pd.notna(row["away_goals"]):
            return f"{int(row['home_goals'])}-{int(row['away_goals'])}"
        return np.nan
    out["score"] = out.apply(_make_score, axis=1)
    # xG — not present in football-data.org files; set to NaN
    if "home_xg" not in out.columns:
        out["home_xg"] = np.nan
    if "away_xg" not in out.columns:
        out["away_xg"] = np.nan
    # venue / referee — required by build_fixture_features
    if "venue" not in out.columns:
        out["venue"] = "Unknown"
    if "referee" not in out.columns:
        out["referee"] = "Unknown"
    return out


def _train_wf_model(
    prior_ml: pd.DataFrame,
    model_name: str = "logistic_regression",
    min_train_rows: int = 30,
) -> tuple[Any, list[str], Optional[str]]:
    """Train an sklearn model on *prior_ml* matches.

    Returns (fitted_model, feature_cols, error_string).
    error_string is None on success; fitted_model is None on failure.

    Leakage guarantee: prior_ml MUST contain only matches with
    date < current cutoff.  This function never touches the target season's
    current matchday.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            table = _build_features(prior_ml, min_history=1)
        table = table.dropna(subset=["result"])
        if len(table) < min_train_rows:
            return None, [], f"only_{len(table)}_rows_after_feature_build"
        if table["result"].nunique() < 2:
            return None, [], "fewer_than_2_classes_in_training_set"

        cols = [c for c in _feature_columns(table) if not table[c].isna().all()]
        X_train = table[cols]
        y_train = table["result"]

        model = _build_pipeline(model_name=model_name)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(X_train, y_train)

        return model, cols, None

    except Exception as exc:           # training must not crash the whole run
        return None, [], str(exc)


def _predict_wf_probs(
    model: Any,
    cols: list[str],
    prior_ml: pd.DataFrame,
    match_row: pd.Series,
) -> tuple[Optional[dict[str, float]], Optional[str]]:
    """Use *model* to predict H/D/A probabilities for a single pre-match row.

    build_fixture_features internally filters prior_ml to date < match_date,
    so even if prior_ml already excludes the current matchday at the caller
    level, the internal filter is a second safety net.
    """
    try:
        oh = match_row.get("odds_home") if pd.notna(match_row.get("odds_home", float("nan"))) else None
        od = match_row.get("odds_draw") if pd.notna(match_row.get("odds_draw", float("nan"))) else None
        oa = match_row.get("odds_away") if pd.notna(match_row.get("odds_away", float("nan"))) else None

        fixture_feats = _build_fixture_features(
            history_df=prior_ml,
            home_team=str(match_row["home_team"]),
            away_team=str(match_row["away_team"]),
            match_date=match_row["date"],
            odds_home=oh,
            odds_draw=od,
            odds_away=oa,
        )

        X = fixture_feats.reindex(columns=cols)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            raw_proba = model.predict_proba(X)
        proba_df = _align_proba(model, raw_proba)

        h = float(proba_df["H"].iloc[0])
        d = float(proba_df["D"].iloc[0])
        a = float(proba_df["A"].iloc[0])

        # Normalise to sum to 1 (guard against floating-point drift)
        total = h + d + a
        if total > 0:
            h, d, a = h / total, d / total, a / total

        return {"home": round(h, 4), "draw": round(d, 4), "away": round(a, 4)}, None

    except Exception as exc:
        return None, str(exc)


def run_walk_forward(
    df: pd.DataFrame,
    min_warmup: int,
    league_name: str,
    retrain_frequency: str = "matchday",
    wf_model_name: str = "logistic_regression",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """TRUE walk-forward ML replay.

    For every matchday group:
    - train_df  = matches with date < cutoff_date  (never includes current group)
    - An ML model is fitted on train_df
    - Probabilities for matches in the current group come from that ML model
    - control/chaos scores come from rolling form stats (unchanged)
    - recommended_market_type/subtype generated as normal

    retrain_frequency:
      'matchday' — new model fitted at every cutoff (default)
      'season'   — model fitted once at the first eligible cutoff, reused for all later

    This function NEVER uses a pre-trained full-season model and NEVER trains
    on the current or future matchday.
    """
    groups = group_by_matchday(df)
    total_matches = len(df)
    match_counter = 0

    pred_rows: list[dict] = []
    eval_rows: list[dict] = []

    # ML-ready view of the full season df
    ml_df = _prepare_for_ml(df)

    # Season-level model cache (used only when retrain_frequency == "season")
    _season_model: Any = None
    _season_cols: list[str] = []
    _season_error: Optional[str] = None
    _season_model_name_str: str = ""
    _season_initialized: bool = False

    skipped_warmup = 0
    training_failures = 0

    for md_label, md_group in groups:
        md_date = md_group["date"].min()

        # Build strictly-prior prior_df — NO current matchday
        if "matchday" in df.columns and df["matchday"].notna().any():
            prior_df  = df[df["matchday"]  < md_label].copy()
            prior_ml  = ml_df[ml_df["matchday"] < md_label].copy()
        else:
            prior_df  = df[df["date"]  < md_date].copy()
            prior_ml  = ml_df[ml_df["date"] < md_date].copy()

        # Hard leakage guard — prior_df and prior_ml must contain NO future dates
        _assert_no_leakage(prior_df, md_date, label=f"walk_forward prior_df md={md_label}")
        _assert_no_leakage(prior_ml, md_date, label=f"walk_forward prior_ml md={md_label}")

        # Build extended features on a recent window (O(n²) performance guard)
        recent_prior = prior_df
        recent_prior = build_extended_features(
            recent_prior,
            include_elo=True, include_h2h=True, include_time_decay=True,
            include_adj_xg=True, include_game_state=True, include_context=True,
        )
        _assert_no_leakage(recent_prior, md_date, "extended_features")

        if len(prior_df) < min_warmup:
            skipped_warmup += len(md_group)
            match_counter  += len(md_group)
            continue

        cutoff_date = str(md_date)[:10]

        # ------------------------------------------------------------------
        # Model training
        # ------------------------------------------------------------------
        if retrain_frequency == "matchday":
            model, cols, model_error = _train_wf_model(prior_ml, wf_model_name)
            model_name_str = wf_model_name if model is not None else ""
            if model is None:
                training_failures += 1
        else:  # "season" — train once at the first eligible cutoff
            if not _season_initialized:
                _season_model, _season_cols, _season_error = _train_wf_model(
                    prior_ml, wf_model_name
                )
                _season_model_name_str = wf_model_name if _season_model is not None else ""
                _season_initialized = True
                if _season_model is None:
                    training_failures += 1
            model          = _season_model
            cols           = _season_cols
            model_error    = _season_error
            model_name_str = _season_model_name_str

        # ------------------------------------------------------------------
        # Per-match predictions
        # ------------------------------------------------------------------
        for _, match in md_group.iterrows():
            match_counter += 1

            # 1. Base features from rolling form / odds (control + chaos)
            features = build_match_features(match, recent_prior, "walk_forward", league_name)
            features["matchday"]        = md_label
            features["cutoff_date"]     = cutoff_date
            features["train_rows"]      = len(prior_ml)
            features["test_group_size"] = len(md_group)
            features["model_name"]      = model_name_str
            features["model_trained_ok"] = model is not None
            features["model_error"]     = model_error or ""

            # 2. If ML model is available, replace probability estimates
            if model is not None:
                ml_probs, pred_error = _predict_wf_probs(model, cols, prior_ml, match)
                if ml_probs is not None:
                    # Override de-vigged / form-based probs with ML probs
                    features["model_home_prob"] = ml_probs["home"]
                    features["model_draw_prob"] = ml_probs["draw"]
                    features["model_away_prob"] = ml_probs["away"]
                    # Re-derive direction and confidence from ML output
                    features["likely_1x2"] = determine_likely_1x2(ml_probs)
                    top_p = max(ml_probs.values())
                    features["confidence"] = determine_confidence(
                        top_p, features["control_score_10"]
                    )
                else:
                    # Model exists but prediction failed for this row
                    features["model_error"] = (
                        (features["model_error"] + "|" if features["model_error"] else "")
                        + (pred_error or "prediction_failed")
                    )

            # 3. Recommended market (uses updated likely_1x2 / confidence)
            rec = build_recommended_market(features)

            pred = {
                **features,
                "recommended_market_type":    rec["recommended_market_type"],
                "recommended_market_subtype":  rec["recommended_market_subtype"],
                "recommended_market_read":     rec["recommended_market_read"],
                "recommendation_strength":     rec["recommendation_strength"],
                "risk_note":                   rec["risk_note"],
            }

            # League-aware profile layer (report interpretation only)
            pred = apply_league_market_profile(pred, league_name)
            # Market tier diagnostic layer (report interpretation only)
            pred = build_market_tier(pred)

            pred_rows.append(pred)

            # 4. Evaluate against actual result
            hg = float(match["home_goals"])
            ag = float(match["away_goals"])
            actuals  = _actual_actuals(hg, ag)
            eval_row = {**pred, **actuals}
            eval_row["type_success"]    = evaluate_type_success(eval_row)
            eval_row["subtype_success"] = evaluate_subtype_success(eval_row)

            eval_row["month"]        = str(match["date"])[:7]
            eval_row["odds_bucket"]  = _odds_bucket(
                eval_row.get("odds_home"), eval_row.get("odds_away"))
            eval_row["ctrl_bucket"]  = _ctrl_bucket(eval_row["control_score_10"])
            eval_row["chaos_bucket"] = _chaos_bucket(eval_row["chaos_score_10"])
            eval_row["fav_side"]     = _fav_side(
                eval_row.get("odds_home"), eval_row.get("odds_away"),
                eval_row.get("odds_draw"))
            eval_row["season_phase"] = _season_phase(match_counter, total_matches)

            eval_rows.append(eval_row)

    if not pred_rows:
        print(f"  [WARN] No matchdays survived the warmup gate (min_warmup={min_warmup}).")
        print(f"         Total matches in file: {len(df)}. Try a smaller --min-warmup-matches.")
    else:
        if skipped_warmup:
            print(f"  Warmup skipped : {skipped_warmup} matches")
        if training_failures:
            print(f"  Training fails : {training_failures} cutoff(s) produced no model")

    pred_df = pd.DataFrame(pred_rows)
    eval_df  = pd.DataFrame(eval_rows)
    return pred_df, eval_df


# ---------------------------------------------------------------------------
# Main replay loop
# ---------------------------------------------------------------------------

def run_replay(
    df: pd.DataFrame,
    mode: str,
    min_warmup: int,
    league_name: str,
    retrain_frequency: str = "matchday",
    wf_model_name: str = "logistic_regression",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Replay all matchdays, building pre-match features then evaluating.

    Returns (predictions_df, evaluation_df).
    Matches with fewer than min_warmup prior matches are skipped.

    When mode == 'walk_forward', routes to run_walk_forward() which performs
    TRUE per-cutoff ML training with strict no-future-leakage.
    """
    if mode == "walk_forward":
        return run_walk_forward(
            df=df,
            min_warmup=min_warmup,
            league_name=league_name,
            retrain_frequency=retrain_frequency,
            wf_model_name=wf_model_name,
        )

    groups = group_by_matchday(df)
    total_matches = len(df)
    match_counter = 0

    pred_rows: list[dict] = []
    eval_rows: list[dict] = []

    for md_label, md_group in groups:
        # prior_df = ALL matches played BEFORE this matchday
        # We use the min date of this group to build the cutoff
        md_date = md_group["date"].min()
        prior_df = df[df["date"] < md_date].copy()

        # Also exclude the current matchday by matchday label if column exists
        if "matchday" in df.columns and df["matchday"].notna().any():
            prior_df = df[df["matchday"] < md_label].copy()

        # Hard leakage guard — must have NO future dates in prior_df
        _assert_no_leakage(prior_df, md_date, label=f"matchday={md_label}")

        # Build extended features on a recent window (O(n²) performance guard)
        recent_prior = prior_df
        recent_prior = build_extended_features(
            recent_prior,
            include_elo=True, include_h2h=True, include_time_decay=True,
            include_adj_xg=True, include_game_state=True, include_context=True,
        )
        _assert_no_leakage(recent_prior, md_date, "extended_features")

        # Warm-up gate: skip if not enough prior data
        if len(prior_df) < min_warmup:
            match_counter += len(md_group)
            continue

        for _, match in md_group.iterrows():
            match_counter += 1

            # Build pre-match features (no future leakage — prior_df is fixed)
            features = build_match_features(match, recent_prior, mode, league_name)
            features["matchday"] = md_label

            # Generate recommended market recommendation
            rec = build_recommended_market(features)

            pred = {**features,
                    "recommended_market_type":    rec["recommended_market_type"],
                    "recommended_market_subtype":  rec["recommended_market_subtype"],
                    "recommended_market_read":     rec["recommended_market_read"],
                    "recommendation_strength":     rec["recommendation_strength"],
                    "risk_note":                   rec["risk_note"]}

            # League-aware profile layer (report interpretation only)
            pred = apply_league_market_profile(pred, league_name)
            # Market tier diagnostic layer (report interpretation only)
            pred = build_market_tier(pred)

            pred_rows.append(pred)

            # Evaluate against actual result
            hg = float(match["home_goals"])
            ag = float(match["away_goals"])
            actuals = _actual_actuals(hg, ag)

            eval_row = {**pred, **actuals}
            eval_row["type_success"]    = evaluate_type_success(eval_row)
            eval_row["subtype_success"] = evaluate_subtype_success(eval_row)

            # Dimension columns
            eval_row["month"]        = str(match["date"])[:7]  # YYYY-MM
            eval_row["odds_bucket"]  = _odds_bucket(
                eval_row.get("odds_home"), eval_row.get("odds_away"))
            eval_row["ctrl_bucket"]  = _ctrl_bucket(eval_row["control_score_10"])
            eval_row["chaos_bucket"] = _chaos_bucket(eval_row["chaos_score_10"])
            eval_row["fav_side"]     = _fav_side(
                eval_row.get("odds_home"), eval_row.get("odds_away"),
                eval_row.get("odds_draw"))
            eval_row["season_phase"] = _season_phase(match_counter, total_matches)

            eval_rows.append(eval_row)

    if not pred_rows:
        print(f"  [WARN] No matchdays survived the warmup gate (min_warmup={min_warmup}).")
        print(f"         Total matches in file: {len(df)}. Try --min-warmup-matches 20.")

    pred_df = pd.DataFrame(pred_rows)
    eval_df  = pd.DataFrame(eval_rows)
    return pred_df, eval_df


# ---------------------------------------------------------------------------
# Summary markdown
# ---------------------------------------------------------------------------

def _rate_line(label: str, grp: pd.DataFrame, col: str, width: int = 22) -> str:
    n    = grp[col].notna().sum()
    hits = int(grp[col].sum()) if n > 0 else 0
    rate = hits / n if n > 0 else 0.0
    warn = "  ⚠ small sample" if n < 20 else ""
    return f"  {label:<{width}} {n:>5} {hits:>5} {rate:>7.1%}{warn}"


def build_summary_markdown(
    eval_df: pd.DataFrame,
    league: str,
    season: str,
    mode: str,
) -> str:
    lines: list[str] = []

    if mode == "walk_forward":
        lines += [
            f"# Season Replay Audit — {league} {season}",
            "",
            "## ✅ TRUE WALK-FORWARD ML MODE",
            "",
            "For every matchday group:",
            "- `train_df` = matches with date < cutoff_date  (strict, zero future leakage)",
            "- An ML model was trained on `train_df` features",
            "- Probabilities for the current group came from that model's `predict_proba`",
            "- No pre-trained full-season model was used",
            "- No current or future match results appear in any training fold",
            "",
        ]
    else:
        lines += [
            f"# Season Replay Audit — {league} {season}",
            "",
        ]

    # Walk-forward model stats
    if mode == "walk_forward" and "model_trained_ok" in eval_df.columns:
        total_cutoffs = eval_df["cutoff_date"].nunique() if "cutoff_date" in eval_df.columns else "n/a"
        failed_rows   = int((eval_df["model_trained_ok"] == False).sum())
        trained_ok    = int((eval_df["model_trained_ok"] == True).sum())
        model_name    = eval_df["model_name"].mode().iloc[0] if "model_name" in eval_df.columns and len(eval_df) > 0 else "n/a"
        lines += [
            "### Walk-Forward Training Summary",
            "",
            f"- ML model used        : {model_name}",
            f"- Distinct cutoff dates: {total_cutoffs}",
            f"- Predictions with OK model : {trained_ok}",
            f"- Predictions with no model : {failed_rows}",
            "",
        ]

    skipped = len(eval_df)   # placeholder; actual skipped not tracked in eval_df
    lines += [
        f"- Mode              : {mode}",
        f"- Total matches     : {len(eval_df)}",
        f"- Evaluatable (type): {eval_df['type_success'].notna().sum()}",
        f"- Data-warning rows : {eval_df['data_warning'].sum() if 'data_warning' in eval_df.columns else 'n/a'}",
        "",
        "*Diagnostic only. No betting claims.*",
        "",
    ]

    # ---- Type success ----
    lines += ["## Success Rate by Recommended Market Type", ""]
    lines.append(f"  {'Type':<22} {'n':>5} {'hits':>5} {'rate':>7}  Notes")
    lines.append("  " + "-" * 60)
    type_rows = []
    for mtype, grp in eval_df.groupby("recommended_market_type"):
        ev = grp[grp["type_success"].notna()]
        n = len(ev); hits = int(ev["type_success"].sum()) if n > 0 else 0
        rate = hits / n if n > 0 else 0.0
        warn = "  ⚠ n<20" if n < 20 else ""
        note = ""
        if mtype == "BTTS_OVER":
            o25 = int((ev["actual_over25"] == 1).sum()) if "actual_over25" in ev else "?"
            bts = int((ev["actual_btts"]   == 1).sum()) if "actual_btts"   in ev else "?"
            note = f"over25={o25}/{n}  btts={bts}/{n}"
        lines.append(f"  {mtype:<22} {n:>5} {hits:>5} {rate:>7.1%}  {note}{warn}")
        type_rows.append({"type": mtype, "n": n, "hits": hits, "rate": rate})
    lines.append("")

    # ---- Subtype success ----
    if "subtype_success" in eval_df.columns:
        sub_ev = eval_df[eval_df["subtype_success"].notna()]
        if not sub_ev.empty:
            lines += ["## Success Rate by Recommended Market Subtype", ""]
            lines.append(f"  {'Subtype':<24} {'n':>5} {'hits':>5} {'rate':>7}  Parent")
            lines.append("  " + "-" * 65)
            sub_rows = []
            for subtype, sg in sub_ev.groupby("recommended_market_subtype"):
                n    = len(sg)
                hits = int(sg["subtype_success"].sum())
                rate = hits / n if n > 0 else 0.0
                parent = sg["recommended_market_type"].mode().iloc[0] if len(sg) > 0 else "?"
                warn = "  ⚠ n<20" if n < 20 else ""
                lines.append(f"  {subtype:<24} {n:>5} {hits:>5} {rate:>7.1%}  {parent}{warn}")
                sub_rows.append({"subtype": subtype, "n": n, "hits": hits, "rate": rate})
            lines.append("")

            # BTTS_OVER split
            bo_ev = sub_ev[sub_ev["recommended_market_type"] == "BTTS_OVER"]
            if not bo_ev.empty:
                lines += ["### BTTS_OVER Subtype Split", ""]
                bo_type = eval_df[eval_df["recommended_market_type"] == "BTTS_OVER"]
                bo_type_ev = bo_type[bo_type["type_success"].notna()]
                bo_n = len(bo_type_ev)
                bo_hits = int(bo_type_ev["type_success"].sum()) if bo_n > 0 else 0
                lines.append(
                    f"  Type-level OR : {bo_hits}/{bo_n}  "
                    f"({bo_hits/bo_n:.1%})" if bo_n > 0 else "  n/a"
                )
                for subtype, sg in bo_ev.groupby("recommended_market_subtype"):
                    sn = len(sg); sh = int(sg["subtype_success"].sum())
                    lines.append(f"  Subtype {subtype:<22}: {sh}/{sn}  ({sh/sn:.1%})")
                lines.append("")

            # Best / worst
            if sub_rows:
                sr = sorted(sub_rows, key=lambda x: x["rate"], reverse=True)
                lines += ["### Best Performing Subtypes"]
                for r in sr[:5]:
                    lines.append(f"  {r['subtype']:<24} {r['rate']:.1%}  ({r['hits']}/{r['n']})")
                lines += ["", "### Worst Performing Subtypes"]
                for r in sorted(sub_rows, key=lambda x: x["rate"])[:5]:
                    lines.append(f"  {r['subtype']:<24} {r['rate']:.1%}  ({r['hits']}/{r['n']})")
                lines.append("")

    # ---- By control ----
    if "ctrl_bucket" in eval_df.columns:
        ev = eval_df[eval_df["type_success"].notna()]
        lines += ["## Success by Control Bucket", ""]
        lines.append(f"  {'Bucket':<20} {'n':>5} {'hits':>5} {'rate':>7}")
        lines.append("  " + "-" * 42)
        for bucket, grp in ev.groupby("ctrl_bucket"):
            lines.append(_rate_line(bucket, grp, "type_success", 20))
        lines.append("")

    # ---- By chaos ----
    if "chaos_bucket" in eval_df.columns:
        ev = eval_df[eval_df["type_success"].notna()]
        lines += ["## Success by Chaos Bucket", ""]
        lines.append(f"  {'Bucket':<20} {'n':>5} {'hits':>5} {'rate':>7}")
        lines.append("  " + "-" * 42)
        for bucket, grp in ev.groupby("chaos_bucket"):
            lines.append(_rate_line(bucket, grp, "type_success", 20))
        lines.append("")

    # ---- By confidence ----
    if "confidence" in eval_df.columns:
        ev = eval_df[eval_df["type_success"].notna()]
        lines += ["## Success by Confidence", ""]
        lines.append(f"  {'Confidence':<16} {'n':>5} {'hits':>5} {'rate':>7}")
        lines.append("  " + "-" * 38)
        for conf, grp in ev.groupby("confidence"):
            lines.append(_rate_line(conf, grp, "type_success", 16))
        lines.append("")

    # ---- By season phase ----
    if "season_phase" in eval_df.columns:
        ev = eval_df[eval_df["type_success"].notna()]
        lines += ["## Success by Season Phase", ""]
        for phase in ["early", "mid", "late"]:
            grp = ev[ev["season_phase"] == phase]
            if len(grp) > 0:
                lines.append(_rate_line(phase, grp, "type_success", 12))
        lines.append("")

    # ---- By odds bucket ----
    if "odds_bucket" in eval_df.columns:
        ev = eval_df[eval_df["type_success"].notna()]
        lines += ["## Success by Odds Bucket", ""]
        for bucket, grp in ev.groupby("odds_bucket"):
            lines.append(_rate_line(bucket, grp, "type_success", 28))
        lines.append("")

    # ---- AVOID diagnostic ----
    avoid_df = eval_df[eval_df["recommended_market_type"] == "AVOID"]
    if len(avoid_df) > 0:
        ev = avoid_df[avoid_df["type_success"].notna()]
        lines += ["## AVOID Diagnostic", ""]
        lines.append(f"  Total AVOID calls  : {len(avoid_df)}")
        if len(ev) > 0:
            lines.append(f"  Correctly avoided  : {int(ev['type_success'].sum())} / {len(ev)}"
                         f"  ({ev['type_success'].mean():.1%})")
            lines.append(
                f"  Note: AVOID 'success' = match was difficult (result≠predicted or high-scoring or draw)."
            )
        lines.append("")

    # ---- UNDER stability ----
    under_df = eval_df[eval_df["recommended_market_type"] == "UNDER"]
    if len(under_df) > 0:
        ev = under_df[under_df["type_success"].notna()]
        lines += ["## UNDER Stability Check", ""]
        if len(ev) > 0:
            u25 = int((ev.get("actual_under25", pd.Series(dtype=float)) == 1).sum()) \
                if "actual_under25" in ev else "?"
            u35 = int((ev.get("actual_under35", pd.Series(dtype=float)) == 1).sum()) \
                if "actual_under35" in ev else "?"
            lines.append(f"  Under 2.5 hit  : {u25}/{len(ev)}")
            lines.append(f"  Under 3.5 hit  : {u35}/{len(ev)}")
            lines.append(f"  Type OR success: {int(ev['type_success'].sum())}/{len(ev)}"
                         f"  ({ev['type_success'].mean():.1%})")
        lines.append("")

    # ---- Top misses ----
    misses = eval_df[(eval_df["type_success"] == False)].head(20)
    if not misses.empty:
        lines += ["## Top 20 Misses", ""]
        lines.append(
            f"  {'Match':<36} {'Type':<16} {'Subtype':<22} {'Actual':<8} {'Goals'}"
        )
        lines.append("  " + "-" * 95)
        for _, row in misses.iterrows():
            game   = f"{row.get('home_team','?')} v {row.get('away_team','?')}"
            mtype  = str(row.get("recommended_market_type","?"))
            stype  = str(row.get("recommended_market_subtype","?"))
            actual = str(row.get("actual_result","?"))
            goals  = row.get("actual_total_goals", "?")
            gstr   = f"{goals:.0f}g" if isinstance(goals, float) and not math.isnan(goals) else "?"
            lines.append(f"  {game[:34]:<36} {mtype:<16} {stype:<22} {actual:<8} {gstr}")
        lines.append("")

    # ---- Top hits ----
    hits = eval_df[(eval_df["type_success"] == True)].head(20)
    if not hits.empty:
        lines += ["## Top 20 Clean Hits", ""]
        lines.append(
            f"  {'Match':<36} {'Type':<16} {'Subtype':<22} {'Actual':<8} {'Goals'}"
        )
        lines.append("  " + "-" * 95)
        for _, row in hits.iterrows():
            game   = f"{row.get('home_team','?')} v {row.get('away_team','?')}"
            mtype  = str(row.get("recommended_market_type","?"))
            stype  = str(row.get("recommended_market_subtype","?"))
            actual = str(row.get("actual_result","?"))
            goals  = row.get("actual_total_goals", "?")
            gstr   = f"{goals:.0f}g" if isinstance(goals, float) and not math.isnan(goals) else "?"
            lines.append(f"  {game[:34]:<36} {mtype:<16} {stype:<22} {actual:<8} {gstr}")
        lines.append("")

    # ---- Warnings ----
    warn_lines = []
    for mtype, grp in eval_df.groupby("recommended_market_type"):
        ev = grp[grp["type_success"].notna()]
        if len(ev) < 20:
            warn_lines.append(f"  ⚠ {mtype}: only {len(ev)} evaluatable matches — interpret with caution.")
    for subtype, grp in eval_df.groupby("recommended_market_subtype"):
        ev = grp[grp["subtype_success"].notna()] if "subtype_success" in grp else pd.DataFrame()
        if len(ev) < 10:
            warn_lines.append(f"  ⚠ subtype {subtype}: only {len(ev)} evaluatable matches.")
    if warn_lines:
        lines += ["## Sample Size Warnings", ""] + warn_lines + [""]

    if mode == "walk_forward":
        lines += [
            "---",
            "## Leakage-Safety Confirmation",
            "",
            "| Check | Status |",
            "|---|---|",
            "| train_df excludes current matchday | ✅ prior_df/prior_ml filtered by date < cutoff_date |",
            "| train_df excludes future matchdays | ✅ strict < not <= cutoff |",
            "| Current match result not used as feature | ✅ build_fixture_features uses history_df[date < match_date] |",
            "| No full-season pre-trained model | ✅ model fitted fresh per cutoff (or once at first eligible) |",
            "| Cross-match contamination on same date | ✅ all matches in a group share the same prior_df snapshot |",
            "",
        ]

    lines += [
        "---",
        "*This report is diagnostic only. No betting, staking, or ROI claims.*",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_outputs(
    pred_df: pd.DataFrame,
    eval_df: pd.DataFrame,
    league: str,
    season: str,
    mode: str,
    out_dir: Path,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = league.lower().replace(" ", "_").replace(".", "")

    pred_path = out_dir / f"{slug}_{season}_predictions.csv"
    eval_path = out_dir / f"{slug}_{season}_evaluation.csv"
    summ_path = out_dir / f"{slug}_{season}_summary.md"

    pred_df.to_csv(pred_path, index=False)
    eval_df.to_csv(eval_path, index=False)

    md = build_summary_markdown(eval_df, league, season, mode)
    summ_path.write_text(md, encoding="utf-8")

    print(f"  Predictions : {pred_path}  ({len(pred_df)} rows)")
    print(f"  Evaluation  : {eval_path}  ({len(eval_df)} rows)")
    print(f"  Summary     : {summ_path}")


def _append_all_replay_summary(
    eval_df: pd.DataFrame,
    league: str,
    season: str,
    mode: str,
    out_dir: Path,
) -> None:
    """Append/create the cross-run all_replay_summary.csv."""
    summ_path = out_dir / "all_replay_summary.csv"
    ev = eval_df[eval_df["type_success"].notna()]
    row = {
        "league": league,
        "season": season,
        "mode": mode,
        "total_matches": len(eval_df),
        "evaluatable_matches": len(ev),
        "overall_type_success_rate": round(ev["type_success"].mean(), 4) if len(ev) > 0 else None,
    }
    for mtype, grp in ev.groupby("recommended_market_type"):
        n = len(grp); hits = int(grp["type_success"].sum())
        key = mtype.lower()
        row[f"{key}_n"] = n
        row[f"{key}_rate"] = round(hits / n, 4) if n > 0 else None

    if summ_path.exists():
        existing = pd.read_csv(summ_path)
        # Replace if same league+season+mode exists
        mask = ~((existing["league"] == league) & (existing["season"] == season)
                 & (existing["mode"] == mode))
        existing = existing[mask]
        out = pd.concat([existing, pd.DataFrame([row])], ignore_index=True)
    else:
        out = pd.DataFrame([row])

    out.to_csv(summ_path, index=False)
    print(f"  All-run summary: {summ_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    args = build_parser().parse_args()

    div_code, league_name = resolve_league(args.league)
    season = str(args.season)
    out_dir = Path(args.output_dir)

    print(f"\n{'='*60}")
    print(f"  Season Replay Audit")
    print(f"  League : {league_name} ({div_code})")
    print(f"  Season : {season}")
    print(f"  Mode   : {args.mode}")
    if args.mode == "walk_forward":
        print(f"  ML model    : {args.wf_model}")
        print(f"  Retrain freq: {args.retrain_frequency}")
    print(f"{'='*60}\n")

    print("Loading data…")
    df = load_league_data(args.league, season, args.history)
    print(f"  {len(df)} matches loaded from {div_code}_{season}")

    groups = group_by_matchday(df)
    print(f"  {len(groups)} matchday groups")
    print(f"  Warmup gate: {args.min_warmup_matches} prior matches required\n")

    print("Running replay…")
    pred_df, eval_df = run_replay(
        df=df,
        mode=args.mode,
        min_warmup=args.min_warmup_matches,
        league_name=league_name,
        retrain_frequency=args.retrain_frequency,
        wf_model_name=args.wf_model,
    )

    ev = eval_df[eval_df["type_success"].notna()]
    if len(ev) > 0:
        overall = ev["type_success"].mean()
        print(f"\n  Evaluatable matches : {len(ev)}")
        print(f"  Overall type success: {overall:.1%}")
        for mtype, grp in ev.groupby("recommended_market_type"):
            g = grp[grp["type_success"].notna()]
            n = len(g); h = int(g["type_success"].sum())
            print(f"    {mtype:<18} {h}/{n} = {h/n:.1%}")

    print("\nWriting outputs…")
    write_outputs(pred_df, eval_df, league_name, season, args.mode, out_dir)
    _append_all_replay_summary(eval_df, league_name, season, args.mode, out_dir)

    print("\nDone.")


if __name__ == "__main__":
    main()
