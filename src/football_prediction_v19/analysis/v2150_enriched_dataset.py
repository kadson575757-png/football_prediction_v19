# -*- coding: utf-8 -*-
from __future__ import annotations

from collections import defaultdict
import re

import numpy as np
import pandas as pd

from football_prediction_v19.analysis.v2140_goal_ml_dataset import load_v2140_dataset
from football_prediction_v19.analysis.v2150_feature_coverage import GROUP_FEATURES
from football_prediction_v19.analysis.v2150_prematch_data_sources import (
    load_football_data_events,
    load_xg_events,
)


def build_enriched_dataset(
    base_dataset: pd.DataFrame,
    chance_events: pd.DataFrame,
    xg_events: pd.DataFrame,
) -> pd.DataFrame:
    base = base_dataset.copy()
    base["match_date"] = pd.to_datetime(base["match_date"])
    chance_index = _event_index(chance_events)
    xg_index = _event_index(xg_events)
    market_index = _market_index(chance_events)
    records = []
    for _, target in base.iterrows():
        date = target["match_date"]
        competition = str(target["competition"])
        home, away = str(target["home_team"]), str(target["away_team"])
        record = target.to_dict()
        home_chance = _prior(chance_index, competition, home, date)
        away_chance = _prior(chance_index, competition, away, date)
        home_xg = _prior(xg_index, competition, home, date)
        away_xg = _prior(xg_index, competition, away, date)
        _add_chance_features(record, home_chance, away_chance, home, away)
        _add_xg_features(record, home_xg, away_xg, home, away)
        _add_squad_features(record)
        market = market_index.get((competition, date.normalize(), _norm(home), _norm(away)))
        _add_market_features(record, market, date)
        clean_dates = []
        for group in ("EXPECTED_GOALS", "CHANCE_CREATION"):
            for feature in GROUP_FEATURES[group]:
                source_date = pd.to_datetime(record.get(f"{feature}_source_date"), errors="coerce")
                if pd.notna(source_date):
                    clean_dates.append(source_date)
        maximum = max(clean_dates) if clean_dates else pd.NaT
        record["target_match_date"] = date.date().isoformat()
        record["maximum_feature_source_date"] = maximum.date().isoformat() if pd.notna(maximum) else ""
        record["maximum_feature_source_timestamp"] = maximum.isoformat() if pd.notna(maximum) else ""
        record["post_match_rows_used_count"] = int(sum(source_date >= date for source_date in clean_dates))
        record["asof_clean"] = not clean_dates or maximum < date
        records.append(record)
    return pd.DataFrame(records).sort_values(["match_date", "competition", "home_team"]).reset_index(drop=True)


def load_enriched_dataset(project_root: str = ".") -> pd.DataFrame:
    return build_enriched_dataset(
        load_v2140_dataset(project_root),
        load_football_data_events(project_root),
        load_xg_events(project_root),
    )


def _event_index(events: pd.DataFrame) -> dict[tuple[str, str], list[dict[str, object]]]:
    result: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    if events.empty:
        return result
    for _, row in events.sort_values("match_date").iterrows():
        for team in (str(row["home_team"]), str(row["away_team"])):
            result[(str(row["competition"]), _norm(team))].append(row.to_dict())
    return result


def _prior(index, competition: str, team: str, date: pd.Timestamp) -> list[dict[str, object]]:
    return [row for row in index.get((competition, _norm(team)), []) if pd.Timestamp(row["match_date"]) < date]


def _team_values(rows, team: str, home_column: str, away_column: str) -> list[float]:
    values = []
    for row in rows:
        home = _norm(str(row["home_team"])) == _norm(team)
        value = row.get(home_column if home else away_column)
        if pd.notna(value):
            values.append(float(value))
    return values


def _team_against_values(rows, team: str, home_column: str, away_column: str) -> list[float]:
    values = []
    for row in rows:
        home = _norm(str(row["home_team"])) == _norm(team)
        value = row.get(away_column if home else home_column)
        if pd.notna(value):
            values.append(float(value))
    return values


def _mean(values: list[float], window: int | None = None) -> float:
    selected = values[-window:] if window else values
    return float(np.mean(selected)) if selected else np.nan


def _add_chance_features(record, home_rows, away_rows, home, away):
    values = {
        "home_rolling_shots_for": _mean(_team_values(home_rows, home, "home_shots", "away_shots"), 10),
        "home_rolling_shots_against": _mean(_team_against_values(home_rows, home, "home_shots", "away_shots"), 10),
        "away_rolling_shots_for": _mean(_team_values(away_rows, away, "home_shots", "away_shots"), 10),
        "away_rolling_shots_against": _mean(_team_against_values(away_rows, away, "home_shots", "away_shots"), 10),
        "home_rolling_sot_for": _mean(_team_values(home_rows, home, "home_shots_on_target", "away_shots_on_target"), 10),
        "away_rolling_sot_for": _mean(_team_values(away_rows, away, "home_shots_on_target", "away_shots_on_target"), 10),
        "home_rolling_corners_for": _mean(_team_values(home_rows, home, "home_corners", "away_corners"), 10),
        "away_rolling_corners_for": _mean(_team_values(away_rows, away, "home_corners", "away_corners"), 10),
    }
    dates = [pd.Timestamp(row["match_date"]) for row in home_rows + away_rows]
    _apply_metadata(
        record, values, max(dates) if dates else pd.NaT,
        source="FOOTBALL_DATA_MATCH_STATS", quality="HIGH", timestamp_available=True, force_asof_failed=False,
    )


def _add_xg_features(record, home_rows, away_rows, home, away):
    home_for = _team_values(home_rows, home, "home_xg", "away_xg")
    home_against = _team_against_values(home_rows, home, "home_xg", "away_xg")
    away_for = _team_values(away_rows, away, "home_xg", "away_xg")
    away_against = _team_against_values(away_rows, away, "home_xg", "away_xg")
    home_venue = [row for row in home_rows if _norm(str(row["home_team"])) == _norm(home)]
    away_venue = [row for row in away_rows if _norm(str(row["away_team"])) == _norm(away)]
    values = {
        "home_rolling_xg_for": _mean(home_for, 10), "home_rolling_xg_against": _mean(home_against, 10),
        "away_rolling_xg_for": _mean(away_for, 10), "away_rolling_xg_against": _mean(away_against, 10),
        "home_venue_xg_for": _mean(_team_values(home_venue, home, "home_xg", "away_xg"), 10),
        "home_venue_xg_against": _mean(_team_against_values(home_venue, home, "home_xg", "away_xg"), 10),
        "away_venue_xg_for": _mean(_team_values(away_venue, away, "home_xg", "away_xg"), 10),
        "away_venue_xg_against": _mean(_team_against_values(away_venue, away, "home_xg", "away_xg"), 10),
        "home_last5_xg_for": _mean(home_for, 5), "away_last5_xg_for": _mean(away_for, 5),
        "home_xg_difference_per_match": _mean(home_for, 10) - _mean(home_against, 10),
        "away_xg_difference_per_match": _mean(away_for, 10) - _mean(away_against, 10),
        "relative_opponent_adjusted_xg": (
            _mean(home_for, 10) / max(_mean(away_against, 10), .25)
            - _mean(away_for, 10) / max(_mean(home_against, 10), .25)
        ),
    }
    dates = [pd.Timestamp(row["match_date"]) for row in home_rows + away_rows]
    _apply_metadata(
        record, values, max(dates) if dates else pd.NaT,
        source="UNDERSTAT_ACCEPTED_MANUAL_XG", quality="HIGH", timestamp_available=True, force_asof_failed=False,
    )


def _add_squad_features(record):
    values = {feature: np.nan for feature in GROUP_FEATURES["SQUAD_AVAILABILITY"]}
    _apply_metadata(
        record, values, pd.NaT, source="UNAVAILABLE", quality="LOW",
        timestamp_available=False, force_asof_failed=False,
    )


def _market_index(events):
    result = {}
    if events.empty:
        return result
    for _, row in events.iterrows():
        result[(
            str(row["competition"]), pd.Timestamp(row["match_date"]).normalize(),
            _norm(str(row["home_team"])), _norm(str(row["away_team"])),
        )] = row.to_dict()
    return result


def _add_market_features(record, market, target_date):
    if market:
        odds = [market.get("home_odds"), market.get("draw_odds"), market.get("away_odds")]
        implied = [1 / float(value) if pd.notna(value) and float(value) > 0 else np.nan for value in odds]
        total = sum(implied) if all(pd.notna(value) for value in implied) else np.nan
        values = {
            "market_home_implied_probability": implied[0] / total if pd.notna(total) else np.nan,
            "market_draw_implied_probability": implied[1] / total if pd.notna(total) else np.nan,
            "market_away_implied_probability": implied[2] / total if pd.notna(total) else np.nan,
            "market_probability_sum": total,
            "market_margin": total - 1 if pd.notna(total) else np.nan,
        }
        source_date = target_date
    else:
        values = {feature: np.nan for feature in GROUP_FEATURES["MARKET_CONTEXT"]}
        source_date = pd.NaT
    _apply_metadata(
        record, values, source_date, source="FOOTBALL_DATA_OPENING_ODDS", quality="MEDIUM",
        timestamp_available=False, force_asof_failed=True,
    )


def _apply_metadata(record, values, source_date, *, source, quality, timestamp_available, force_asof_failed):
    for feature, value in values.items():
        record[feature] = value
        record[f"{feature}_source"] = source if pd.notna(value) else "UNAVAILABLE"
        record[f"{feature}_source_date"] = source_date.date().isoformat() if pd.notna(source_date) and pd.notna(value) else ""
        record[f"{feature}_source_quality"] = quality if pd.notna(value) else "NONE"
        record[f"{feature}_missing_indicator"] = int(pd.isna(value))
        record[f"{feature}_fallback_used"] = False
        record[f"{feature}_prematch_timestamp_available"] = bool(timestamp_available)
        record[f"{feature}_asof_clean"] = bool(
            pd.isna(value) or (pd.notna(source_date) and not force_asof_failed)
        )


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())
