# -*- coding: utf-8 -*-
from __future__ import annotations

import pandas as pd


GROUP_FEATURES = {
    "EXPECTED_GOALS": [
        "home_rolling_xg_for", "home_rolling_xg_against", "away_rolling_xg_for", "away_rolling_xg_against",
        "home_venue_xg_for", "home_venue_xg_against", "away_venue_xg_for", "away_venue_xg_against",
        "home_last5_xg_for", "away_last5_xg_for", "home_xg_difference_per_match",
        "away_xg_difference_per_match", "relative_opponent_adjusted_xg",
    ],
    "CHANCE_CREATION": [
        "home_rolling_shots_for", "home_rolling_shots_against",
        "away_rolling_shots_for", "away_rolling_shots_against",
        "home_rolling_sot_for", "away_rolling_sot_for",
        "home_rolling_corners_for", "away_rolling_corners_for",
    ],
    "SQUAD_AVAILABILITY": [
        "home_confirmed_absence_count", "away_confirmed_absence_count",
        "home_lineup_continuity", "away_lineup_continuity",
        "home_goalkeeper_change", "away_goalkeeper_change",
    ],
    "MARKET_CONTEXT": [
        "market_home_implied_probability", "market_draw_implied_probability",
        "market_away_implied_probability", "market_probability_sum", "market_margin",
    ],
}


def feature_coverage(dataset: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for group, features in GROUP_FEATURES.items():
        for feature in features:
            available = dataset[feature].notna()
            source_dates = pd.to_datetime(dataset.loc[available, f"{feature}_source_date"], errors="coerce")
            rows.append({
                "feature_group": group, "feature": feature,
                "available_count": int(available.sum()), "missing_count": int((~available).sum()),
                "available_rate": float(available.mean()),
                "competition_count": int(dataset.loc[available, "competition"].nunique()),
                "season_count": int(dataset.loc[available, "season"].nunique()),
                "team_count": int(pd.concat([
                    dataset.loc[available, "home_team"], dataset.loc[available, "away_team"]
                ]).nunique()),
                "earliest_available_date": str(source_dates.min().date()) if source_dates.notna().any() else "",
                "latest_available_date": str(source_dates.max().date()) if source_dates.notna().any() else "",
                "prematch_timestamp_available": bool(dataset[f"{feature}_prematch_timestamp_available"].all()),
                "asof_clean_count": int(dataset.loc[available, f"{feature}_asof_clean"].sum()),
                "asof_failed_count": int((available & ~dataset[f"{feature}_asof_clean"]).sum()),
                "source_name": _mode(dataset.loc[available, f"{feature}_source"]),
                "source_quality": _mode(dataset.loc[available, f"{feature}_source_quality"]),
                "usable_for_modeling": False,
            })
    coverage = pd.DataFrame(rows)
    gates = group_coverage_gates(dataset, coverage)
    gate_map = gates.set_index("feature_group")["passes_main_coverage_gate"].to_dict()
    coverage["usable_for_modeling"] = coverage["feature_group"].map(gate_map).fillna(False)
    return coverage


def group_coverage_gates(dataset: pd.DataFrame, coverage: pd.DataFrame | None = None) -> pd.DataFrame:
    rows = []
    for group, features in GROUP_FEATURES.items():
        row_available = dataset[features].notna().all(axis=1)
        comp_counts = dataset.loc[row_available, "competition"].value_counts()
        dominance = float(comp_counts.max() / comp_counts.sum()) if comp_counts.sum() else 0.0
        timestamp_ok = all(bool(dataset[f"{feature}_prematch_timestamp_available"].all()) for feature in features)
        asof_failed = sum(int((dataset[feature].notna() & ~dataset[f"{feature}_asof_clean"]).sum()) for feature in features)
        rate = float(row_available.mean())
        passes = (
            rate >= .70 and dataset.loc[row_available, "competition"].nunique() >= 3
            and dataset.loc[row_available, "season"].nunique() >= 2
            and timestamp_ok and asof_failed == 0 and dominance <= .60
        )
        rows.append({
            "feature_group": group, "available_count": int(row_available.sum()),
            "available_rate": rate,
            "competition_count": int(dataset.loc[row_available, "competition"].nunique()),
            "season_count": int(dataset.loc[row_available, "season"].nunique()),
            "prematch_timestamp_available": timestamp_ok, "asof_failed_count": asof_failed,
            "dominant_competition_share": dominance,
            "coverage_tier": "MAIN" if passes else "SUBSET" if .40 <= rate < .70 else "DOCUMENT_ONLY",
            "passes_main_coverage_gate": passes,
        })
    return pd.DataFrame(rows)


def coverage_by_competition_season(dataset: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (competition, season), group_rows in dataset.groupby(["competition", "season"]):
        for feature_group, features in GROUP_FEATURES.items():
            available = group_rows[features].notna().all(axis=1)
            for phase_name, phase_mask in {
                "EARLY": group_rows["season_phase"].le(.33),
                "MIDDLE": group_rows["season_phase"].gt(.33) & group_rows["season_phase"].le(.66),
                "LATE": group_rows["season_phase"].gt(.66),
            }.items():
                subset = available[phase_mask]
                rows.append({
                    "grouping_dimension": "COMPETITION_SEASON_PHASE",
                    "competition": competition, "season": season, "season_phase": phase_name,
                    "home_team": "", "away_team": "",
                    "feature_group": feature_group, "rows": int(phase_mask.sum()),
                    "available_count": int(subset.sum()),
                    "available_rate": float(subset.mean()) if len(subset) else 0.0,
                })
    for team_column, dimension in (("home_team", "HOME_TEAM"), ("away_team", "AWAY_TEAM")):
        for (competition, season, team), team_rows in dataset.groupby(["competition", "season", team_column]):
            for feature_group, features in GROUP_FEATURES.items():
                available = team_rows[features].notna().all(axis=1)
                rows.append({
                    "grouping_dimension": dimension, "competition": competition, "season": season,
                    "season_phase": "ALL", "home_team": team if team_column == "home_team" else "",
                    "away_team": team if team_column == "away_team" else "",
                    "feature_group": feature_group, "rows": len(team_rows),
                    "available_count": int(available.sum()), "available_rate": float(available.mean()),
                })
    return pd.DataFrame(rows)


def _mode(values: pd.Series) -> str:
    clean = values.dropna().astype(str)
    return clean.mode().iloc[0] if len(clean) else ""
