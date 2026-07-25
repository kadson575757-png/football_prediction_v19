# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from football_prediction_v19.analysis.v2130_goal_distribution import load_local_goal_results
from football_prediction_v19.analysis.v2130_rolling_goal_features import build_rolling_goal_features


TARGET_COLUMNS = ["actual_home_goals", "actual_away_goals"]
CATEGORICAL_COLUMNS = ["competition"]
NUMERIC_COLUMNS = [
    "league_home_goals_mean", "league_away_goals_mean", "rolling_league_total_goal_rate",
    "season_phase", "matchweek_proxy",
    "home_overall_goals_for_rate", "home_overall_goals_against_rate",
    "away_overall_goals_for_rate", "away_overall_goals_against_rate",
    "home_goal_difference_per_match", "away_goal_difference_per_match",
    "home_points_per_match", "away_points_per_match",
    "home_prior_matches_count", "away_prior_matches_count",
    "home_home_goals_for_rate", "home_home_goals_against_rate",
    "away_away_goals_for_rate", "away_away_goals_against_rate",
    "home_venue_points_per_match", "away_venue_points_per_match",
    "home_venue_history_count", "away_venue_history_count",
    "home_last5_goals_for", "home_last5_goals_against", "away_last5_goals_for", "away_last5_goals_against",
    "home_last5_points", "away_last5_points",
    "home_last10_goals_for", "home_last10_goals_against", "away_last10_goals_for", "away_last10_goals_against",
    "home_last10_points", "away_last10_points",
    "home_form_trend", "away_form_trend",
    "home_attack_strength", "home_defense_strength", "away_attack_strength", "away_defense_strength",
    "home_opponent_adjusted_goals_for", "home_opponent_adjusted_goals_against",
    "away_opponent_adjusted_goals_for", "away_opponent_adjusted_goals_against",
    "relative_strength_gap",
    "base_home_probability", "base_draw_probability", "base_away_probability", "base_probability_edge",
]


def load_existing_probability_context(project_root: str | Path) -> pd.DataFrame:
    root = Path(project_root)
    paths = [
        root / "outputs/v2124_pl_multi_season_robustness/v2124_combined_rows.csv",
        root / "outputs/v2126_external_league_edge_calibration/v2126_external_rows.csv",
    ]
    frames = []
    for path in paths:
        if not path.exists():
            continue
        frame = pd.read_csv(path, keep_default_na=False)
        if "competition" not in frame.columns:
            frame["competition"] = "Premier League"
        else:
            frame["competition"] = frame["competition"].replace("", "Premier League")
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    frame = pd.concat(frames, ignore_index=True)
    frame["match_date"] = pd.to_datetime(frame["match_date"], errors="coerce")
    return frame[[
        "competition", "season", "match_date", "home_team", "away_team",
        "home_win_probability", "draw_probability", "away_win_probability", "probability_edge",
    ]].rename(columns={
        "home_win_probability": "base_home_probability",
        "draw_probability": "base_draw_probability",
        "away_win_probability": "base_away_probability",
        "probability_edge": "base_probability_edge",
    }).drop_duplicates(["competition", "season", "match_date", "home_team", "away_team"])


def build_goal_ml_dataset(
    matches: pd.DataFrame,
    *,
    probability_context: pd.DataFrame | None = None,
) -> pd.DataFrame:
    features = build_rolling_goal_features(matches)
    features["match_date"] = pd.to_datetime(features["match_date"])
    features["rolling_league_total_goal_rate"] = features["league_home_goals_mean"] + features["league_away_goals_mean"]
    within_season = features.groupby(["competition", "season"]).cumcount()
    team_count = features.groupby(["competition", "season"])["home_team"].transform("nunique").clip(lower=2)
    features["matchweek_proxy"] = (within_season / (team_count / 2)).astype(int) + 1
    features["season_phase"] = (features["matchweek_proxy"] / 38.0).clip(upper=1.0)
    features["home_form_trend"] = features["home_last5_goals_for"] - features["home_last10_goals_for"]
    features["away_form_trend"] = features["away_last5_goals_for"] - features["away_last10_goals_for"]
    features["home_opponent_adjusted_goals_for"] = features["home_overall_goals_for_rate"] / features["away_defense_strength"].clip(lower=.25)
    features["home_opponent_adjusted_goals_against"] = features["home_overall_goals_against_rate"] / features["away_attack_strength"].clip(lower=.25)
    features["away_opponent_adjusted_goals_for"] = features["away_overall_goals_for_rate"] / features["home_defense_strength"].clip(lower=.25)
    features["away_opponent_adjusted_goals_against"] = features["away_overall_goals_against_rate"] / features["home_attack_strength"].clip(lower=.25)
    features["relative_strength_gap"] = (
        features["home_attack_strength"] - features["home_defense_strength"]
        - features["away_attack_strength"] + features["away_defense_strength"]
    )
    if probability_context is not None and not probability_context.empty:
        context = probability_context.copy()
        context["match_date"] = pd.to_datetime(context["match_date"], errors="coerce")
        features = features.merge(
            context,
            on=["competition", "season", "match_date", "home_team", "away_team"],
            how="left",
        )
    for column, fallback in (
        ("base_home_probability", 0.34), ("base_draw_probability", 0.32),
        ("base_away_probability", 0.34), ("base_probability_edge", 0.0),
    ):
        if column not in features:
            features[column] = np.nan
        features[f"{column}_missing"] = features[column].isna().astype(int)
    for column in NUMERIC_COLUMNS:
        if column not in features:
            features[column] = np.nan
        features[f"{column}_missing"] = features[column].isna().astype(int)
    # Targets are carried only for evaluation; every feature above was computed before the target row was appended.
    return features.sort_values(["match_date", "competition", "home_team"]).reset_index(drop=True)


def load_v2140_dataset(project_root: str | Path = ".") -> pd.DataFrame:
    matches = load_local_goal_results(project_root)
    context = load_existing_probability_context(project_root)
    return build_goal_ml_dataset(matches, probability_context=context)


def feature_columns() -> tuple[list[str], list[str]]:
    missing = [f"{column}_missing" for column in NUMERIC_COLUMNS]
    return NUMERIC_COLUMNS + missing, CATEGORICAL_COLUMNS
