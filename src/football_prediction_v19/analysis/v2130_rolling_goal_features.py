# -*- coding: utf-8 -*-
from __future__ import annotations

from collections import defaultdict

import pandas as pd


DEFAULT_HOME_GOALS = 1.45
DEFAULT_AWAY_GOALS = 1.15


def prepare_matches(rows: pd.DataFrame) -> pd.DataFrame:
    frame = rows.copy()
    aliases = {
        "date": "match_date", "league": "competition", "home_goals": "actual_home_goals",
        "away_goals": "actual_away_goals", "FTHG": "actual_home_goals", "FTAG": "actual_away_goals",
        "HomeTeam": "home_team", "AwayTeam": "away_team",
    }
    for source, target in aliases.items():
        if target not in frame and source in frame:
            frame[target] = frame[source]
    required = ["match_date", "competition", "season", "home_team", "away_team", "actual_home_goals", "actual_away_goals"]
    for column in required:
        if column not in frame:
            frame[column] = pd.NA
    frame["match_date"] = pd.to_datetime(frame["match_date"], errors="coerce")
    frame["actual_home_goals"] = pd.to_numeric(frame["actual_home_goals"], errors="coerce")
    frame["actual_away_goals"] = pd.to_numeric(frame["actual_away_goals"], errors="coerce")
    frame = frame.dropna(subset=required).sort_values(["competition", "match_date", "home_team", "away_team"]).reset_index(drop=True)
    frame["actual_result"] = [
        "HOME" if home > away else "AWAY" if away > home else "DRAW"
        for home, away in zip(frame["actual_home_goals"], frame["actual_away_goals"])
    ]
    return frame


def build_rolling_goal_features(rows: pd.DataFrame) -> pd.DataFrame:
    frame = prepare_matches(rows)
    records: list[dict[str, object]] = []
    for competition, group in frame.groupby("competition", sort=False):
        league: list[dict[str, object]] = []
        teams: dict[str, list[dict[str, object]]] = defaultdict(list)
        home_venue: dict[str, list[dict[str, object]]] = defaultdict(list)
        away_venue: dict[str, list[dict[str, object]]] = defaultdict(list)
        for _, row in group.iterrows():
            target_date = row["match_date"]
            home = str(row["home_team"])
            away = str(row["away_team"])
            league_prior = [match for match in league if match["date"] < target_date]
            home_hist = [match for match in teams[home] if match["date"] < target_date]
            away_hist = [match for match in teams[away] if match["date"] < target_date]
            home_venue_prior = [match for match in home_venue[home] if match["date"] < target_date]
            away_venue_prior = [match for match in away_venue[away] if match["date"] < target_date]
            league_home = _mean(league_prior, "home_goals", DEFAULT_HOME_GOALS)
            league_away = _mean(league_prior, "away_goals", DEFAULT_AWAY_GOALS)
            league_team = (league_home + league_away) / 2.0
            home_gf = _team_mean(home_hist, home, "gf", league_team)
            home_ga = _team_mean(home_hist, home, "ga", league_team)
            away_gf = _team_mean(away_hist, away, "gf", league_team)
            away_ga = _team_mean(away_hist, away, "ga", league_team)
            home_count, away_count = len(home_hist), len(away_hist)
            minimum = min(home_count, away_count)
            quality = "READY" if minimum >= 10 else "LOW_HISTORY" if minimum >= 5 else "INSUFFICIENT_HISTORY"
            fallback = minimum < 5
            prior_dates = [match["date"] for match in league_prior]
            record = row.to_dict()
            record.update({
                "target_match_date": target_date.date().isoformat(),
                "maximum_source_date": max(prior_dates).date().isoformat() if prior_dates else "",
                "post_match_rows_used_count": int(sum(date >= target_date for date in prior_dates)),
                "asof_clean": not prior_dates or max(prior_dates) < target_date,
                "league_prior_matches_count": len(league_prior),
                "home_prior_matches_count": home_count,
                "away_prior_matches_count": away_count,
                "history_quality": quality,
                "fallback_applied": fallback,
                "league_home_goals_mean": league_home,
                "league_away_goals_mean": league_away,
                "home_attack_strength": home_gf / league_team,
                "home_defense_strength": home_ga / league_team,
                "away_attack_strength": away_gf / league_team,
                "away_defense_strength": away_ga / league_team,
                "home_overall_goals_for_rate": home_gf,
                "home_overall_goals_against_rate": home_ga,
                "away_overall_goals_for_rate": away_gf,
                "away_overall_goals_against_rate": away_ga,
                "home_goal_difference_per_match": home_gf - home_ga,
                "away_goal_difference_per_match": away_gf - away_ga,
                "home_points_per_match": _points_mean(home_hist, home),
                "away_points_per_match": _points_mean(away_hist, away),
                "home_venue_history_count": len(home_venue_prior),
                "away_venue_history_count": len(away_venue_prior),
                "home_home_goals_for_rate": _mean(home_venue_prior, "home_goals", league_home),
                "home_home_goals_against_rate": _mean(home_venue_prior, "away_goals", league_away),
                "away_away_goals_for_rate": _mean(away_venue_prior, "away_goals", league_away),
                "away_away_goals_against_rate": _mean(away_venue_prior, "home_goals", league_home),
                "home_venue_points_per_match": _venue_points(home_venue_prior, home=True),
                "away_venue_points_per_match": _venue_points(away_venue_prior, home=False),
                "home_last5_goals_for": _team_mean(home_hist[-5:], home, "gf", league_team),
                "home_last5_goals_against": _team_mean(home_hist[-5:], home, "ga", league_team),
                "away_last5_goals_for": _team_mean(away_hist[-5:], away, "gf", league_team),
                "away_last5_goals_against": _team_mean(away_hist[-5:], away, "ga", league_team),
                "home_last5_points": _points_mean(home_hist[-5:], home),
                "away_last5_points": _points_mean(away_hist[-5:], away),
                "home_last10_goals_for": _team_mean(home_hist[-10:], home, "gf", league_team),
                "home_last10_goals_against": _team_mean(home_hist[-10:], home, "ga", league_team),
                "away_last10_goals_for": _team_mean(away_hist[-10:], away, "gf", league_team),
                "away_last10_goals_against": _team_mean(away_hist[-10:], away, "ga", league_team),
                "home_last10_points": _points_mean(home_hist[-10:], home),
                "away_last10_points": _points_mean(away_hist[-10:], away),
                "home_form5_attack_factor": _recent_factor(home_hist, home, 5, league_team),
                "away_form5_attack_factor": _recent_factor(away_hist, away, 5, league_team),
                "home_form10_attack_factor": _recent_factor(home_hist, home, 10, league_team),
                "away_form10_attack_factor": _recent_factor(away_hist, away, 10, league_team),
                "home_venue_attack_strength": _mean(home_venue_prior, "home_goals", home_gf) / max(league_home, 0.1),
                "home_venue_defense_strength": _mean(home_venue_prior, "away_goals", home_ga) / max(league_away, 0.1),
                "away_venue_attack_strength": _mean(away_venue_prior, "away_goals", away_gf) / max(league_away, 0.1),
                "away_venue_defense_strength": _mean(away_venue_prior, "home_goals", away_ga) / max(league_home, 0.1),
                "venue_history_ready": len(home_venue_prior) >= 5 and len(away_venue_prior) >= 5,
            })
            records.append(record)
            match = {
                "date": target_date, "home_team": home, "away_team": away,
                "home_goals": float(row["actual_home_goals"]), "away_goals": float(row["actual_away_goals"]),
            }
            league.append(match)
            teams[home].append(match)
            teams[away].append(match)
            home_venue[home].append(match)
            away_venue[away].append(match)
    return pd.DataFrame(records)


def _mean(rows: list[dict[str, object]], column: str, fallback: float) -> float:
    return sum(float(row[column]) for row in rows) / len(rows) if rows else fallback


def _team_mean(rows: list[dict[str, object]], team: str, field: str, fallback: float) -> float:
    if not rows:
        return fallback
    values = []
    for row in rows:
        home = row["home_team"] == team
        if field == "gf":
            values.append(float(row["home_goals"] if home else row["away_goals"]))
        else:
            values.append(float(row["away_goals"] if home else row["home_goals"]))
    return sum(values) / len(values)


def _recent_factor(rows: list[dict[str, object]], team: str, window: int, baseline: float) -> float:
    value = _team_mean(rows[-window:], team, "gf", baseline)
    return max(0.7, min(value / max(baseline, 0.1), 1.3))


def _points_mean(rows: list[dict[str, object]], team: str) -> float:
    if not rows:
        return 1.0
    points = []
    for row in rows:
        is_home = row["home_team"] == team
        gf = float(row["home_goals"] if is_home else row["away_goals"])
        ga = float(row["away_goals"] if is_home else row["home_goals"])
        points.append(3.0 if gf > ga else 1.0 if gf == ga else 0.0)
    return sum(points) / len(points)


def _venue_points(rows: list[dict[str, object]], *, home: bool) -> float:
    if not rows:
        return 1.0
    points = []
    for row in rows:
        gf = float(row["home_goals"] if home else row["away_goals"])
        ga = float(row["away_goals"] if home else row["home_goals"])
        points.append(3.0 if gf > ga else 1.0 if gf == ga else 0.0)
    return sum(points) / len(points)
