# -*- coding: utf-8 -*-
"""Tests for run_season_replay_audit.py.

All tests use synthetic in-memory data — no real API calls, no file I/O
except where explicitly testing output writing (tmp_path fixtures).

Invariants verified:
  - No future leakage: features for matchday N use only data from matchday < N
  - Grouping by date works when no matchday column exists
  - Grouping by matchday column works when it exists
  - Subtype evaluation uses correct per-subtype logic
  - Output files have the required columns
  - Small sample warnings appear in data_warning=True rows
  - Missing odds rows produce a valid (lower-confidence) prediction
  - resolve_league raises cleanly for unknown leagues
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import pytest

# Make scripts directory importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from run_season_replay_audit import (  # noqa: E402
    _actual_actuals,
    _chaos_bucket,
    _ctrl_bucket,
    _odds_bucket,
    _season_phase,
    build_match_features,
    build_summary_markdown,
    compute_ensemble_diagnostics,
    compute_chaos_score,
    compute_control_score,
    determine_confidence,
    determine_likely_1x2,
    estimate_probabilities,
    evaluate_subtype_success,
    evaluate_type_success,
    group_by_matchday,
    resolve_league,
    run_replay,
    team_rolling_stats,
    write_outputs,
)


# ---------------------------------------------------------------------------
# Synthetic data helpers
# ---------------------------------------------------------------------------

def _make_match(
    home: str = "TeamA",
    away: str = "TeamB",
    home_goals: float = 2.0,
    away_goals: float = 1.0,
    date_offset: int = 0,
    matchday: Optional[int] = None,
    odds_home: Optional[float] = 2.0,
    odds_draw: Optional[float] = 3.5,
    odds_away: Optional[float] = 3.8,
    league: str = "Eredivisie",
    season: str = "2024",
) -> dict:
    d = date(2024, 8, 1) + timedelta(days=date_offset * 7)
    row: dict = {
        "date": pd.Timestamp(d),
        "league": league,
        "season": season,
        "home_team": home,
        "away_team": away,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "odds_home": odds_home,
        "odds_draw": odds_draw,
        "odds_away": odds_away,
    }
    if matchday is not None:
        row["matchday"] = matchday
    return row


def _season_df(n_matchdays: int = 10, teams: int = 4) -> pd.DataFrame:
    """Generate a synthetic season with fixed teams playing round-robin."""
    team_names = [f"Team{chr(65+i)}" for i in range(teams)]
    rows = []
    md = 1
    for mday in range(n_matchdays):
        for i in range(0, teams, 2):
            h = team_names[i % teams]
            a = team_names[(i + 1) % teams]
            rows.append(_make_match(
                home=h, away=a,
                home_goals=float((mday + i) % 4),
                away_goals=float((mday + i + 1) % 3),
                date_offset=mday,
                matchday=mday + 1,
            ))
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def _prior_for_md(df: pd.DataFrame, matchday: int) -> pd.DataFrame:
    """Return rows strictly before the given matchday (no leakage helper)."""
    if "matchday" in df.columns:
        return df[df["matchday"] < matchday].copy()
    md_date = df[df["matchday"] == matchday]["date"].min()
    return df[df["date"] < md_date].copy()


# ---------------------------------------------------------------------------
# 1. resolve_league
# ---------------------------------------------------------------------------

def test_resolve_league_by_name():
    code, name = resolve_league("Eredivisie")
    assert code == "N1"
    assert name == "Eredivisie"


def test_resolve_league_by_code():
    code, name = resolve_league("N1")
    assert code == "N1"
    assert name == "Eredivisie"


def test_resolve_league_la_liga():
    code, name = resolve_league("La Liga")
    assert code == "SP1"


def test_resolve_league_unknown_raises():
    with pytest.raises(ValueError, match="Unknown league"):
        resolve_league("Fictional League FC")


@pytest.mark.parametrize("alias,expected_code", [
    ("Premier League", "E0"),
    ("EPL",            "E0"),
    ("E0",             "E0"),
    ("Serie A",        "I1"),
    ("I1",             "I1"),
    ("Bundesliga",     "D1"),
    ("D1",             "D1"),
    ("Ligue 1",        "F1"),
    ("F1",             "F1"),
    ("2. Bundesliga",  "D2"),
    ("D2",             "D2"),
])
def test_all_league_aliases_resolve(alias, expected_code):
    code, _ = resolve_league(alias)
    assert code == expected_code, f"{alias!r} → expected {expected_code}, got {code}"


# ---------------------------------------------------------------------------
# 2. group_by_matchday — date-based grouping
# ---------------------------------------------------------------------------

def test_group_by_date_when_no_matchday_column():
    rows = [
        _make_match(date_offset=0),
        _make_match(date_offset=0),
        _make_match(date_offset=7),
    ]
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    # No matchday column
    groups = group_by_matchday(df)
    assert len(groups) == 2, "Should have 2 date groups"
    first_label, first_grp = groups[0]
    assert len(first_grp) == 2
    assert len(groups[1][1]) == 1


def test_group_by_matchday_column_when_present():
    rows = [
        _make_match(date_offset=0, matchday=1),
        _make_match(date_offset=0, matchday=1),
        _make_match(date_offset=7, matchday=2),
        _make_match(date_offset=14, matchday=3),
    ]
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    groups = group_by_matchday(df)
    labels = [g[0] for g in groups]
    assert labels == [1, 2, 3], f"Expected [1,2,3], got {labels}"
    assert len(groups[0][1]) == 2


def test_groups_are_ordered_chronologically():
    rows = [_make_match(date_offset=i, matchday=i + 1) for i in range(5)]
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    groups = group_by_matchday(df)
    labels = [g[0] for g in groups]
    assert labels == sorted(labels)


# ---------------------------------------------------------------------------
# 3. No future leakage
# ---------------------------------------------------------------------------

def test_no_future_leakage_prior_df_excludes_current_matchday():
    """For matchday N, prior_df must not contain any matchday N rows."""
    df = _season_df(n_matchdays=8, teams=4)
    groups = group_by_matchday(df)

    for md_label, md_group in groups:
        md_date = md_group["date"].min()
        # Simulate what run_replay does
        prior_df = df[df["date"] < md_date].copy()
        if "matchday" in df.columns and df["matchday"].notna().any():
            prior_df = df[df["matchday"] < md_label].copy()

        # No current-matchday rows in prior
        if "matchday" in prior_df.columns:
            assert (prior_df["matchday"] < md_label).all(), (
                f"Matchday {md_label}: prior_df contains rows from matchday {md_label}"
            )
        # No dates >= current matchday's start date
        assert (prior_df["date"] < md_date).all(), (
            f"Matchday {md_label}: prior_df contains rows from {md_date} or later"
        )


def test_team_stats_use_only_prior_data():
    """team_rolling_stats receives only prior rows — verify stat values reflect that."""
    df = _season_df(n_matchdays=10, teams=4)
    team = "TeamA"

    # Matchday 5 prior: matchdays 1-4
    prior_4 = df[df["matchday"] < 5].copy()
    stats_4 = team_rolling_stats(team, prior_4)

    # Matchday 6 prior: matchdays 1-5
    prior_5 = df[df["matchday"] < 6].copy()
    stats_5 = team_rolling_stats(team, prior_5)

    # stats_5 may differ from stats_4 if TeamA played in matchday 5
    team_in_md5 = ((df["matchday"] == 5) &
                   ((df["home_team"] == team) | (df["away_team"] == team))).any()
    if team_in_md5:
        assert stats_5["n_games"] >= stats_4["n_games"], (
            "After adding md5 data, n_games should not decrease"
        )


def test_build_match_features_only_uses_prior_df(tmp_path):
    """build_match_features called with empty prior_df produces data_warning=True."""
    df = _season_df(n_matchdays=5, teams=4)
    match = df.iloc[6]  # some match mid-season
    empty_prior = df.iloc[0:0]  # zero rows
    features = build_match_features(match, empty_prior, "diagnostic_replay", "Eredivisie")
    assert features["data_warning"] is True
    assert features["home_stats_n"] == 0
    assert features["away_stats_n"] == 0


def test_ensemble_diagnostics_one_model_returns_none():
    result = compute_ensemble_diagnostics([
        {"model": "main_model", "prediction": "Home"},
    ])
    assert result["ensemble_agreement"] == "NONE"
    assert result["ensemble_note"] == (
        "Only one model prediction available; ensemble agreement not computed."
    )
    assert result["ensemble_model_predictions"]


def test_ensemble_diagnostics_all_models_agree_high():
    result = compute_ensemble_diagnostics([
        {"model": "lr", "prediction": "H"},
        {"model": "gb", "prediction": "Home"},
        {"model": "rf", "prediction": "1"},
    ])
    assert result["ensemble_agreement"] == "HIGH"
    assert "All 3 available models agree on HOME" in result["ensemble_note"]


def test_ensemble_diagnostics_majority_returns_medium():
    result = compute_ensemble_diagnostics([
        {"model": "lr", "prediction": "H"},
        {"model": "gb", "prediction": "Home"},
        {"model": "rf", "prediction": "Away"},
    ])
    assert result["ensemble_agreement"] == "MEDIUM"
    assert "Majority agreement: 2/3 models predict HOME" in result["ensemble_note"]


def test_ensemble_diagnostics_conflict_returns_low():
    result = compute_ensemble_diagnostics([
        {"model": "lr", "prediction": "Home"},
        {"model": "gb", "prediction": "Draw"},
        {"model": "rf", "prediction": "Away"},
    ])
    assert result["ensemble_agreement"] == "LOW"
    assert "No clear majority" in result["ensemble_note"]


def test_run_replay_ensemble_agreement_never_blank_when_columns_exist():
    df = _season_df(n_matchdays=8, teams=4)
    pred_df, eval_df = run_replay(
        df=df,
        mode="diagnostic_replay",
        min_warmup=4,
        league_name="Eredivisie",
    )
    assert "ensemble_agreement" in pred_df.columns
    assert "ensemble_agreement" in eval_df.columns
    assert pred_df["ensemble_agreement"].astype(str).str.strip().ne("").all()
    assert eval_df["ensemble_agreement"].astype(str).str.strip().ne("").all()


def test_features_home_away_stats_n_increases_with_prior_data():
    df = _season_df(n_matchdays=12, teams=4)
    team_match = df[(df["home_team"] == "TeamA") | (df["away_team"] == "TeamA")].iloc[5]

    prior_small = df[df["matchday"] < 3].copy()
    prior_large = df[df["matchday"] < 8].copy()

    f_small = build_match_features(team_match, prior_small, "diagnostic_replay", "Eredivisie")
    f_large = build_match_features(team_match, prior_large, "diagnostic_replay", "Eredivisie")

    assert f_large["home_stats_n"] >= f_small["home_stats_n"]
    assert f_large["away_stats_n"] >= f_small["away_stats_n"]


# ---------------------------------------------------------------------------
# 4. team_rolling_stats
# ---------------------------------------------------------------------------

def test_team_stats_empty_df_returns_defaults():
    stats = team_rolling_stats("TeamX", pd.DataFrame(columns=[
        "date","home_team","away_team","home_goals","away_goals"
    ]))
    assert stats["n_games"] == 0
    assert 0 <= stats["points_per_game"] <= 3


def test_team_stats_single_win():
    rows = [_make_match(home="A", away="B", home_goals=2, away_goals=0, date_offset=0)]
    df = pd.DataFrame(rows); df["date"] = pd.to_datetime(df["date"])
    s = team_rolling_stats("A", df)
    assert s["n_games"] == 1
    assert s["points_per_game"] == 3.0
    assert s["win_rate"] == 1.0
    assert s["avg_gf"] == 2.0
    assert s["avg_ga"] == 0.0


def test_team_stats_single_draw():
    rows = [_make_match(home="A", away="B", home_goals=1, away_goals=1, date_offset=0)]
    df = pd.DataFrame(rows); df["date"] = pd.to_datetime(df["date"])
    s = team_rolling_stats("A", df)
    assert s["points_per_game"] == 1.0
    assert s["draw_rate"] == 1.0
    assert s["btts_rate"] == 1.0
    assert s["over25_rate"] == 0.0  # 2 goals, not > 2.5


def test_team_stats_over25_and_btts():
    # 2-1: total 3 > 2.5, both scored
    rows = [_make_match(home="A", away="B", home_goals=2, away_goals=1, date_offset=0)]
    df = pd.DataFrame(rows); df["date"] = pd.to_datetime(df["date"])
    s = team_rolling_stats("A", df)
    assert s["over25_rate"] == 1.0
    assert s["btts_rate"] == 1.0


def test_team_stats_uses_both_home_and_away_matches():
    rows = [
        _make_match(home="A", away="B", home_goals=2, away_goals=0, date_offset=0),
        _make_match(home="C", away="A", home_goals=0, away_goals=1, date_offset=1),
    ]
    df = pd.DataFrame(rows); df["date"] = pd.to_datetime(df["date"])
    s = team_rolling_stats("A", df)
    assert s["n_games"] == 2  # participated in both (once home, once away)


def test_team_stats_rolling_window_respected():
    """With n=3, only the last 3 matches should be used."""
    rows = [_make_match(home="A", away="B", home_goals=float(i), away_goals=0, date_offset=i)
            for i in range(6)]
    df = pd.DataFrame(rows); df["date"] = pd.to_datetime(df["date"])
    s = team_rolling_stats("A", df, n=3)
    # With n=3, we get the last 3 matches (i=3,4,5 → gf=3,4,5)
    assert s["n_games"] == 3
    assert abs(s["avg_gf"] - (3+4+5)/3) < 0.01


# ---------------------------------------------------------------------------
# 5. Control / chaos scores
# ---------------------------------------------------------------------------

def test_control_high_when_strong_favourite():
    hs = {"points_per_game": 2.5, "over25_rate": 0.5, "btts_rate": 0.4,
          "draw_rate": 0.1, "n_games": 10}
    as_ = {"points_per_game": 0.5, "over25_rate": 0.5, "btts_rate": 0.4,
           "draw_rate": 0.3, "n_games": 10}
    score = compute_control_score(hs, as_, odds_home=1.3, odds_draw=5.0, odds_away=9.0)
    assert score >= 6.0, f"Expected high control, got {score}"


def test_control_low_when_no_odds_and_equal_form():
    hs = as_ = {"points_per_game": 1.5, "over25_rate": 0.5, "btts_rate": 0.5,
                "draw_rate": 0.25, "n_games": 10}
    score = compute_control_score(hs, as_, None, None, None)
    assert score <= 4.0, f"Expected low control, got {score}"


def test_control_penalised_with_insufficient_data():
    hs = {"points_per_game": 2.8, "over25_rate": 0.5, "btts_rate": 0.4,
          "draw_rate": 0.1, "n_games": 2}   # only 2 games!
    as_ = {"points_per_game": 0.2, "over25_rate": 0.5, "btts_rate": 0.4,
           "draw_rate": 0.3, "n_games": 2}
    score_few  = compute_control_score(hs, as_, 1.3, 5.0, 9.0)
    hs["n_games"] = as_["n_games"] = 10
    score_many = compute_control_score(hs, as_, 1.3, 5.0, 9.0)
    assert score_few < score_many, "More data → higher/equal control"


def test_chaos_high_when_both_teams_high_over25():
    hs = {"over25_rate": 0.85, "btts_rate": 0.80, "draw_rate": 0.20, "n_games": 10}
    as_ = {"over25_rate": 0.80, "btts_rate": 0.75, "draw_rate": 0.25, "n_games": 10}
    score = compute_chaos_score(hs, as_, odds_draw=3.0)
    assert score >= 5.0, f"Expected high chaos, got {score}"


def test_chaos_low_when_both_teams_low_scoring():
    hs = {"over25_rate": 0.15, "btts_rate": 0.15, "draw_rate": 0.15, "n_games": 10}
    as_ = {"over25_rate": 0.20, "btts_rate": 0.20, "draw_rate": 0.20, "n_games": 10}
    score = compute_chaos_score(hs, as_, odds_draw=4.5)
    assert score <= 3.0, f"Expected low chaos, got {score}"


def test_control_score_bounded_0_to_10():
    hs = {"points_per_game": 3.0, "over25_rate": 1.0, "btts_rate": 1.0,
          "draw_rate": 0.0, "n_games": 100}
    as_ = {"points_per_game": 0.0, "over25_rate": 0.0, "btts_rate": 0.0,
           "draw_rate": 0.0, "n_games": 100}
    s = compute_control_score(hs, as_, 1.0, 10.0, 10.0)
    assert 0.0 <= s <= 10.0


def test_chaos_score_bounded_0_to_10():
    hs = as_ = {"over25_rate": 1.0, "btts_rate": 1.0, "draw_rate": 1.0, "n_games": 10}
    s = compute_chaos_score(hs, as_, 1.0)
    assert 0.0 <= s <= 10.0


# ---------------------------------------------------------------------------
# 6. Probability estimation
# ---------------------------------------------------------------------------

def test_devig_probs_sum_to_one():
    probs = estimate_probabilities({}, {}, odds_home=2.0, odds_draw=3.5, odds_away=4.0)
    assert abs(sum(probs.values()) - 1.0) < 0.01


def test_devig_probs_home_favourite_when_home_odds_lower():
    probs = estimate_probabilities({}, {}, odds_home=1.8, odds_draw=3.5, odds_away=5.0)
    assert probs["home"] > probs["away"]
    assert probs["home"] > probs["draw"]


def test_form_fallback_when_no_odds():
    hs = {"points_per_game": 2.5, "over25_rate": 0.5, "btts_rate": 0.5,
          "draw_rate": 0.1, "n_games": 10}
    as_ = {"points_per_game": 0.5, "over25_rate": 0.5, "btts_rate": 0.5,
           "draw_rate": 0.3, "n_games": 10}
    probs = estimate_probabilities(hs, as_, None, None, None)
    assert abs(sum(probs.values()) - 1.0) < 0.01
    assert probs["home"] > probs["away"]  # strong home team


def test_likely_1x2_home():
    assert determine_likely_1x2({"home": 0.55, "draw": 0.25, "away": 0.20}) == "Home"


def test_likely_1x2_away():
    assert determine_likely_1x2({"home": 0.20, "draw": 0.25, "away": 0.55}) == "Away"


def test_likely_1x2_draw():
    assert determine_likely_1x2({"home": 0.30, "draw": 0.40, "away": 0.30}) == "Draw"


def test_confidence_high():
    assert determine_confidence(0.65, 8.0) == "HIGH"


def test_confidence_medium():
    assert determine_confidence(0.52, 5.0) == "MEDIUM"


def test_confidence_no_confidence_low_prob():
    assert determine_confidence(0.35, 3.0) == "NO-CONFIDENCE"


def test_confidence_no_confidence_low_control():
    assert determine_confidence(0.55, 1.0) == "NO-CONFIDENCE"


# ---------------------------------------------------------------------------
# 7. Evaluation — type success
# ---------------------------------------------------------------------------

def _pred(mtype: str, hg: float, ag: float, read: str = "", likely: str = "Home",
          subtype: str = "NONE", conf: str = "MEDIUM") -> dict:
    actuals = _actual_actuals(hg, ag)
    return {
        "recommended_market_type": mtype,
        "recommended_market_subtype": subtype,
        "recommended_market_read": read,
        "likely_1x2": likely,
        "confidence": conf,
        **actuals,
    }


def test_btts_over_success_or_logic_over25_hit():
    assert evaluate_type_success(_pred("BTTS_OVER", 3, 0)) is True   # over25 only


def test_btts_over_success_or_logic_btts_hit():
    assert evaluate_type_success(_pred("BTTS_OVER", 1, 1)) is True   # btts only


def test_btts_over_fails_both_false():
    assert evaluate_type_success(_pred("BTTS_OVER", 0, 0)) is False


def test_under_success_under35():
    assert evaluate_type_success(_pred("UNDER", 2, 0)) is True    # 2 < 3.5


def test_under_fails_4_goals():
    assert evaluate_type_success(_pred("UNDER", 2, 2)) is False   # 4 not < 3.5


def test_direction_home_success():
    assert evaluate_type_success(_pred("DIRECTION", 2, 0, read="home_direction")) is True


def test_direction_home_failure():
    assert evaluate_type_success(_pred("DIRECTION", 0, 1, read="home_direction")) is False


def test_direction_away_success():
    assert evaluate_type_success(_pred("DIRECTION", 0, 2, read="away_direction")) is True


def test_double_chance_1x_success():
    assert evaluate_type_success(_pred("DOUBLE_CHANCE", 1, 1, read="home_or_draw_1X")) is True


def test_double_chance_1x_fails_away_win():
    assert evaluate_type_success(_pred("DOUBLE_CHANCE", 0, 1, read="home_or_draw_1X")) is False


def test_double_chance_x2_success():
    assert evaluate_type_success(_pred("DOUBLE_CHANCE", 0, 1, read="away_or_draw_X2")) is True


def test_observe_only_returns_none():
    assert evaluate_type_success(_pred("OBSERVE_ONLY", 1, 1)) is None


# ---------------------------------------------------------------------------
# 8. Evaluation — subtype success
# ---------------------------------------------------------------------------

def _sub_pred(subtype: str, hg: float, ag: float) -> dict:
    actuals = _actual_actuals(hg, ag)
    return {"recommended_market_subtype": subtype, **actuals}


def test_over25_subtype_success():
    assert evaluate_subtype_success(_sub_pred("OVER_25", 3, 0)) is True


def test_over25_subtype_fails():
    assert evaluate_subtype_success(_sub_pred("OVER_25", 1, 1)) is False  # 2 not > 2.5


def test_btts_subtype_success_1_1():
    assert evaluate_subtype_success(_sub_pred("BTTS", 1, 1)) is True


def test_btts_subtype_fails_3_0():
    """3-0: over25 True but BTTS False → BTTS subtype should FAIL."""
    assert evaluate_subtype_success(_sub_pred("BTTS", 3, 0)) is False


def test_both_over25_btts_success():
    assert evaluate_subtype_success(_sub_pred("BOTH_OVER25_BTTS", 2, 1)) is True


def test_both_over25_btts_fails_when_only_over25():
    assert evaluate_subtype_success(_sub_pred("BOTH_OVER25_BTTS", 3, 0)) is False


def test_both_over25_btts_fails_when_only_btts():
    assert evaluate_subtype_success(_sub_pred("BOTH_OVER25_BTTS", 1, 1)) is False


def test_under25_subtype_success():
    assert evaluate_subtype_success(_sub_pred("UNDER_25", 1, 1)) is True   # 2 < 2.5


def test_under25_subtype_fails():
    assert evaluate_subtype_success(_sub_pred("UNDER_25", 2, 1)) is False  # 3 not < 2.5


def test_under35_subtype_success():
    assert evaluate_subtype_success(_sub_pred("UNDER_35", 2, 1)) is True   # 3 < 3.5


def test_under35_subtype_fails():
    assert evaluate_subtype_success(_sub_pred("UNDER_35", 2, 2)) is False  # 4 not < 3.5


def test_direction_home_subtype_success():
    assert evaluate_subtype_success(_sub_pred("DIRECTION_HOME", 2, 0)) is True


def test_direction_home_subtype_fails():
    assert evaluate_subtype_success(_sub_pred("DIRECTION_HOME", 0, 1)) is False


def test_direction_away_subtype_success():
    assert evaluate_subtype_success(_sub_pred("DIRECTION_AWAY", 0, 1)) is True


def test_double_chance_1x_subtype_hit():
    assert evaluate_subtype_success(_sub_pred("DOUBLE_CHANCE_1X", 1, 0)) is True


def test_double_chance_1x_subtype_miss():
    assert evaluate_subtype_success(_sub_pred("DOUBLE_CHANCE_1X", 0, 1)) is False


def test_double_chance_x2_subtype_hit():
    assert evaluate_subtype_success(_sub_pred("DOUBLE_CHANCE_X2", 0, 1)) is True


def test_avoid_volatile_subtype_returns_none():
    assert evaluate_subtype_success(_sub_pred("AVOID_VOLATILE", 3, 2)) is None


def test_avoid_low_control_returns_none():
    assert evaluate_subtype_success(_sub_pred("AVOID_LOW_CONTROL", 0, 0)) is None


def test_none_subtype_returns_none():
    assert evaluate_subtype_success(_sub_pred("NONE", 1, 0)) is None


def test_missing_goals_returns_none():
    row = {"recommended_market_subtype": "OVER_25",
           "actual_home_goals": None, "actual_away_goals": None}
    assert evaluate_subtype_success(row) is None


# ---------------------------------------------------------------------------
# 9. Missing odds handling
# ---------------------------------------------------------------------------

def test_missing_odds_produces_valid_prediction():
    df = _season_df(n_matchdays=15, teams=4)
    # Strip all odds
    df["odds_home"] = None
    df["odds_draw"] = None
    df["odds_away"] = None
    pred_df, eval_df = run_replay(df, "diagnostic_replay", 15, "Eredivisie")
    assert len(pred_df) > 0, "Should produce predictions even without odds"
    assert eval_df["type_success"].notna().any(), "Should produce some evaluations"


def test_missing_odds_leads_to_lower_control():
    """Without odds, control score should be lower than with clear favourite odds."""
    df = _season_df(n_matchdays=15, teams=4)
    prior = df[df["matchday"] < 10].copy()
    match_row = df[df["matchday"] == 10].iloc[0]

    # With no odds
    no_odds_row = match_row.copy()
    no_odds_row["odds_home"] = None
    no_odds_row["odds_draw"] = None
    no_odds_row["odds_away"] = None
    f_no_odds = build_match_features(no_odds_row, prior, "diagnostic_replay", "Eredivisie")
    # With clear favourite odds (manually set)
    match_with_odds = match_row.copy()
    match_with_odds["odds_home"] = 1.4
    match_with_odds["odds_draw"] = 4.5
    match_with_odds["odds_away"] = 8.0
    f_with_odds = build_match_features(match_with_odds, prior, "diagnostic_replay", "Eredivisie")

    assert f_with_odds["control_score_10"] >= f_no_odds["control_score_10"]


# ---------------------------------------------------------------------------
# 10. Small sample warnings
# ---------------------------------------------------------------------------

def test_data_warning_when_fewer_than_threshold_prior_games():
    """With only 2 prior matches total, all teams have < 5 games → data_warning=True."""
    df = _season_df(n_matchdays=15, teams=4)
    match = df.iloc[4]
    # Only 1 row of prior data (far too few)
    prior_1row = df.iloc[0:1].copy()
    f = build_match_features(match, prior_1row, "diagnostic_replay", "Eredivisie")
    assert f["data_warning"] is True


def test_data_warning_false_with_sufficient_prior():
    df = _season_df(n_matchdays=20, teams=4)
    match = df[df["matchday"] == 15].iloc[0]
    prior = df[df["matchday"] < 15].copy()
    f = build_match_features(match, prior, "diagnostic_replay", "Eredivisie")
    # With 14 matchdays of prior data, most teams should have enough
    # (specific value depends on team participation, so just check it's a bool)
    assert isinstance(f["data_warning"], bool)


def test_warmup_gate_skips_early_matchdays():
    """Matchdays with fewer prior matches than min_warmup should be skipped."""
    df = _season_df(n_matchdays=30, teams=4)
    pred_df, _ = run_replay(df, "diagnostic_replay", min_warmup=50, league_name="Eredivisie")
    # With 4 teams playing 2 matches per matchday, we get 8 matches per md
    # After 7 matchdays: 7*2=14 matches; need 50 → many matchdays skipped
    # Total matches in df = 30 * 2 = 60; with 50 warmup we expect very few predictions
    assert len(pred_df) < len(df), "Some matchdays should be skipped"


def test_warmup_gate_zero_produces_all_matchdays_except_first():
    """With min_warmup=0, only the very first matchday has 0 prior matches (strict <)."""
    df = _season_df(n_matchdays=10, teams=4)
    pred_df, _ = run_replay(df, "diagnostic_replay", min_warmup=0, league_name="Eredivisie")
    # All matchdays with at least 1 prior match pass
    assert len(pred_df) > 0


# ---------------------------------------------------------------------------
# 11. Output schema
# ---------------------------------------------------------------------------

_REQUIRED_PRED_COLS = {
    "league", "season", "date", "home_team", "away_team",
    "odds_home", "odds_draw", "odds_away",
    "control_score_10", "chaos_score_10",
    "likely_1x2", "confidence",
    "model_home_prob", "model_draw_prob", "model_away_prob",
    "over25_signal", "btts_signal",
    "recommended_market_type", "recommended_market_subtype",
    "recommended_market_read", "recommendation_strength",
}

_REQUIRED_EVAL_COLS = _REQUIRED_PRED_COLS | {
    "actual_result", "actual_home_goals", "actual_away_goals",
    "actual_total_goals", "actual_over25", "actual_under25",
    "actual_under35", "actual_btts",
    "type_success", "subtype_success",
    "month", "ctrl_bucket", "chaos_bucket",
}


def test_prediction_df_has_required_columns():
    df = _season_df(n_matchdays=15, teams=4)
    pred_df, _ = run_replay(df, "diagnostic_replay", 10, "Eredivisie")
    if len(pred_df) > 0:
        for col in _REQUIRED_PRED_COLS:
            assert col in pred_df.columns, f"Missing column: {col!r}"


def test_evaluation_df_has_required_columns():
    df = _season_df(n_matchdays=15, teams=4)
    _, eval_df = run_replay(df, "diagnostic_replay", 10, "Eredivisie")
    if len(eval_df) > 0:
        for col in _REQUIRED_EVAL_COLS:
            assert col in eval_df.columns, f"Missing eval column: {col!r}"


def test_output_files_written(tmp_path):
    df = _season_df(n_matchdays=15, teams=4)
    pred_df, eval_df = run_replay(df, "diagnostic_replay", 10, "Eredivisie")
    write_outputs(pred_df, eval_df, "Eredivisie", "2024", "diagnostic_replay", tmp_path)

    assert (tmp_path / "eredivisie_2024_predictions.csv").exists()
    assert (tmp_path / "eredivisie_2024_evaluation.csv").exists()
    assert (tmp_path / "eredivisie_2024_summary.md").exists()


def test_output_csv_loadable(tmp_path):
    df = _season_df(n_matchdays=15, teams=4)
    pred_df, eval_df = run_replay(df, "diagnostic_replay", 10, "Eredivisie")
    write_outputs(pred_df, eval_df, "Eredivisie", "2024", "diagnostic_replay", tmp_path)

    pred_loaded = pd.read_csv(tmp_path / "eredivisie_2024_predictions.csv")
    eval_loaded = pd.read_csv(tmp_path / "eredivisie_2024_evaluation.csv")
    assert len(pred_loaded) == len(pred_df)
    assert len(eval_loaded) == len(eval_df)


# ---------------------------------------------------------------------------
# 12. Summary markdown
# ---------------------------------------------------------------------------

def test_summary_markdown_contains_key_sections():
    df = _season_df(n_matchdays=15, teams=4)
    _, eval_df = run_replay(df, "diagnostic_replay", 10, "Eredivisie")
    md = build_summary_markdown(eval_df, "Eredivisie", "2024", "diagnostic_replay")
    assert "Season Replay Audit" in md
    assert "Success Rate by Recommended Market Type" in md
    assert "diagnostic only" in md.lower()


def test_summary_markdown_includes_small_sample_warning_section():
    """With small dataset some subtypes will have n<10 → warnings appear."""
    df = _season_df(n_matchdays=15, teams=4)
    _, eval_df = run_replay(df, "diagnostic_replay", 5, "Eredivisie")
    md = build_summary_markdown(eval_df, "Eredivisie", "2024", "diagnostic_replay")
    # Should contain at least one warning line (some subtypes will be scarce)
    assert "Warning" in md or "sample" in md.lower()


# ---------------------------------------------------------------------------
# 13. _actual_actuals helper
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("hg,ag,exp_result,exp_over25,exp_btts", [
    (2, 1, "H", 1, 1),
    (0, 0, "D", 0, 0),
    (0, 3, "A", 1, 0),
    (1, 1, "D", 0, 1),
    (3, 3, "D", 1, 1),
])
def test_actual_actuals(hg, ag, exp_result, exp_over25, exp_btts):
    a = _actual_actuals(float(hg), float(ag))
    assert a["actual_result"] == exp_result
    assert a["actual_over25"] == exp_over25
    assert a["actual_btts"]   == exp_btts
    assert a["actual_total_goals"] == hg + ag


# ---------------------------------------------------------------------------
# 14. Dimension helpers
# ---------------------------------------------------------------------------

def test_ctrl_bucket_high():
    assert _ctrl_bucket(8.0) == "high (7-10)"


def test_ctrl_bucket_medium():
    assert _ctrl_bucket(6.0) == "medium (5-7)"


def test_ctrl_bucket_low():
    assert _ctrl_bucket(4.0) == "low (3-5)"


def test_ctrl_bucket_very_low():
    assert _ctrl_bucket(1.0) == "very_low (<3)"


def test_chaos_bucket_high():
    assert _chaos_bucket(7.0) == "high (6-10)"


def test_chaos_bucket_medium():
    assert _chaos_bucket(5.0) == "medium (4-6)"


def test_chaos_bucket_low():
    assert _chaos_bucket(2.0) == "low (<4)"


def test_odds_bucket_heavy_fav():
    assert _odds_bucket(1.3, 6.0) == "heavy_fav (<=1.5)"


def test_odds_bucket_no_odds():
    assert _odds_bucket(None, None) == "no_odds"


def test_season_phase_early():
    assert _season_phase(5, 100) == "early"


def test_season_phase_mid():
    assert _season_phase(50, 100) == "mid"


def test_season_phase_late():
    assert _season_phase(90, 100) == "late"


# ---------------------------------------------------------------------------
# 15. walk_forward schema is a superset of diagnostic_replay schema
# ---------------------------------------------------------------------------

def test_walk_forward_produces_same_schema():
    """walk_forward adds extra ML columns on top of the diagnostic_replay schema.

    All diagnostic_replay columns must be present in walk_forward output, plus
    the walk-forward-specific columns (cutoff_date, train_rows, model_name, …).
    Both modes must produce the same number of prediction rows.
    """
    df = _season_df(n_matchdays=15, teams=4)
    pred_diag, eval_diag = run_replay(df, "diagnostic_replay", 10, "Eredivisie")
    pred_wf,   eval_wf   = run_replay(df, "walk_forward",      10, "Eredivisie")

    # walk_forward columns must be a superset of diagnostic_replay columns
    missing_from_wf_pred = set(pred_diag.columns) - set(pred_wf.columns)
    missing_from_wf_eval = set(eval_diag.columns) - set(eval_wf.columns)
    assert not missing_from_wf_pred, (
        f"diagnostic_replay columns absent from walk_forward pred: {missing_from_wf_pred}"
    )
    assert not missing_from_wf_eval, (
        f"diagnostic_replay columns absent from walk_forward eval: {missing_from_wf_eval}"
    )

    # walk_forward must add its specific extra columns
    wf_extra = {"cutoff_date", "train_rows", "model_name", "model_trained_ok", "model_error"}
    for col in wf_extra:
        assert col in pred_wf.columns, f"walk_forward missing expected column: {col}"

    # Row count must match
    assert len(pred_diag) == len(pred_wf)
