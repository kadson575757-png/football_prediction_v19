"""Chronological dynamic-rating candidates for the v2.18.0 shadow challenger."""

from __future__ import annotations

import math
from collections import defaultdict, deque

import numpy as np
import pandas as pd


RATING_FAMILIES = ("ELO_RESULT", "ELO_GOAL_DIFFERENCE", "BRADLEY_TERRY_STYLE")
K_FACTORS = (10, 20, 30)
HOME_ADVANTAGES = (40, 60, 80)
SEASON_SHRINKAGES = (0.2, 0.4, 0.6)
INITIAL_RATING = 1500.0


def candidate_configs() -> list[dict[str, object]]:
    return [
        {
            "rating_model": family,
            "k_factor": k,
            "home_advantage": advantage,
            "season_shrinkage": shrinkage,
            "config_name": f"{family}_K{k}_HA{advantage}_S{int(shrinkage * 100)}",
        }
        for family in RATING_FAMILIES
        for k in K_FACTORS
        for advantage in HOME_ADVANTAGES
        for shrinkage in SEASON_SHRINKAGES
    ]


def build_rating_features(rows: pd.DataFrame, config: dict[str, object]) -> pd.DataFrame:
    frame = rows.copy().sort_values(["match_date", "competition", "home_team", "away_team"]).reset_index(drop=True)
    ratings: dict[tuple[str, str], float] = defaultdict(lambda: INITIAL_RATING)
    venue_home: dict[tuple[str, str], float] = defaultdict(lambda: INITIAL_RATING)
    venue_away: dict[tuple[str, str], float] = defaultdict(lambda: INITIAL_RATING)
    histories: dict[tuple[str, str], deque[float]] = defaultdict(lambda: deque(maxlen=10))
    counts: dict[tuple[str, str], int] = defaultdict(int)
    source_dates: dict[str, list[pd.Timestamp]] = defaultdict(list)
    last_season: dict[str, str] = {}
    records: list[dict[str, object]] = []
    for _, row in frame.iterrows():
        competition, season = str(row["competition"]), str(row["season"])
        if last_season.get(competition) not in (None, season):
            shrink = float(config["season_shrinkage"])
            for key in [key for key in ratings if key[0] == competition]:
                ratings[key] = INITIAL_RATING + (ratings[key] - INITIAL_RATING) * (1.0 - shrink)
                venue_home[key] = INITIAL_RATING + (venue_home[key] - INITIAL_RATING) * (1.0 - shrink)
                venue_away[key] = INITIAL_RATING + (venue_away[key] - INITIAL_RATING) * (1.0 - shrink)
        season_shrink = last_season.get(competition) not in (None, season)
        last_season[competition] = season
        home, away = str(row["home_team"]), str(row["away_team"])
        hk, ak = (competition, home), (competition, away)
        home_rating, away_rating = ratings[hk], ratings[ak]
        diff = home_rating + float(config["home_advantage"]) - away_rating
        home_no_draw = 1.0 / (1.0 + 10.0 ** (-diff / 400.0))
        uncertainty = 1.0 / math.sqrt(min(counts[hk], counts[ak]) + 1.0)
        draw_probability = float(np.clip(0.28 - abs(diff) / 2200.0 + uncertainty * 0.03, 0.16, 0.34))
        probabilities = {
            "rating_home_probability": (1.0 - draw_probability) * home_no_draw,
            "rating_draw_probability": draw_probability,
            "rating_away_probability": (1.0 - draw_probability) * (1.0 - home_no_draw),
        }
        target_date = pd.Timestamp(row["match_date"])
        prior_dates = [date for date in source_dates[competition] if date < target_date]
        records.append({
            **row.to_dict(),
            **probabilities,
            "home_rating": home_rating,
            "away_rating": away_rating,
            "rating_difference": diff,
            "rating_home_advantage": float(config["home_advantage"]),
            "home_venue_rating": venue_home[hk],
            "away_venue_rating": venue_away[ak],
            "rating_momentum_last5": _momentum(histories[hk], 5) - _momentum(histories[ak], 5),
            "rating_momentum_last10": _momentum(histories[hk], 10) - _momentum(histories[ak], 10),
            "rating_uncertainty": uncertainty,
            "history_count": min(counts[hk], counts[ak]),
            "season_start_shrinkage_applied": season_shrink,
            "promoted_team_fallback": counts[hk] == 0 or counts[ak] == 0,
            "rating_source": "PRIOR_COMPETITION_HISTORY" if min(counts[hk], counts[ak]) else "LEAGUE_AVERAGE_INITIAL_RATING",
            "fallback_used": counts[hk] == 0 or counts[ak] == 0,
            "fallback_reason": "NO_PRIOR_COMPETITION_HISTORY" if counts[hk] == 0 or counts[ak] == 0 else "",
            "uncertainty_level": "HIGH" if min(counts[hk], counts[ak]) < 5 else "MEDIUM" if min(counts[hk], counts[ak]) < 15 else "LOW",
            "target_match_date": target_date.date().isoformat(),
            "maximum_source_date": max(prior_dates).date().isoformat() if prior_dates else "",
            "maximum_source_timestamp": max(prior_dates).isoformat() if prior_dates else "",
            "post_match_rows_used_count": 0,
            "asof_clean": True,
            "rating_config": config["config_name"],
        })
        actual = str(row["actual_result"])
        score = 1.0 if actual == "HOME" else 0.5 if actual == "DRAW" else 0.0
        multiplier = 1.0
        if config["rating_model"] == "ELO_GOAL_DIFFERENCE":
            margin = abs(float(row["actual_home_goals"]) - float(row["actual_away_goals"]))
            multiplier = min(2.0, 1.0 + 0.25 * margin)
        if config["rating_model"] == "BRADLEY_TERRY_STYLE" and actual == "DRAW":
            multiplier = 0.65
        delta = float(config["k_factor"]) * multiplier * (score - home_no_draw)
        ratings[hk] += delta
        ratings[ak] -= delta
        venue_home[hk] += 0.5 * delta
        venue_away[ak] -= 0.5 * delta
        histories[hk].append(delta)
        histories[ak].append(-delta)
        counts[hk] += 1
        counts[ak] += 1
        source_dates[competition].append(target_date)
    return pd.DataFrame(records)


def select_rating_config(rating_frames: dict[str, pd.DataFrame], train_indices: np.ndarray) -> str:
    if len(train_indices) < 20:
        return sorted(rating_frames)[0]
    ordered = np.asarray(train_indices)
    split = max(1, int(len(ordered) * 0.8))
    validation = ordered[split:]
    scores = []
    for name, frame in rating_frames.items():
        actual = frame.iloc[validation]["actual_result"].to_numpy()
        predicted = frame.iloc[validation][
            ["rating_home_probability", "rating_draw_probability", "rating_away_probability"]
        ].to_numpy().argmax(axis=1)
        target = pd.Categorical(actual, categories=["HOME", "DRAW", "AWAY"]).codes
        scores.append((float(np.mean(predicted == target)), name))
    return max(scores, key=lambda item: (item[0], item[1]))[1]


def _momentum(values: deque[float], window: int) -> float:
    selected = list(values)[-window:]
    return float(np.mean(selected)) if selected else 0.0
