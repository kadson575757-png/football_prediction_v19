# -*- coding: utf-8 -*-
"""Importer registry foundation.

No importer in this registry performs network calls or requires credentials.
Placeholder entries document future integration points only.
"""
from __future__ import annotations

from typing import Any

from football_prediction_v19.data_contracts import (
    OPTIONAL_CONTEXT_COLUMNS,
    OPTIONAL_ODDS_COLUMNS,
    OPTIONAL_XG_COLUMNS,
    REQUIRED_MATCH_COLUMNS,
)

IMPORTER_STATUSES = ("ACTIVE", "PLACEHOLDER", "DISABLED")

IMPORTER_REGISTRY: dict[str, dict[str, Any]] = {
    "football_data_csv": {
        "importer_id": "football_data_csv",
        "source_type": "csv",
        "description": "football-data.co.uk style historical match CSV importer.",
        "required_inputs": ["csv_path"],
        "produces_columns": [*REQUIRED_MATCH_COLUMNS, *OPTIONAL_ODDS_COLUMNS],
        "status": "ACTIVE",
    },
    "fixture_csv": {
        "importer_id": "fixture_csv",
        "source_type": "csv",
        "description": "Local fixture CSV foundation for future daily analysis inputs.",
        "required_inputs": ["csv_path"],
        "produces_columns": [
            "Date",
            "HomeTeam",
            "AwayTeam",
            *OPTIONAL_CONTEXT_COLUMNS,
            *OPTIONAL_ODDS_COLUMNS,
        ],
        "status": "ACTIVE",
    },
    "api_football_placeholder": {
        "importer_id": "api_football_placeholder",
        "source_type": "api",
        "description": "Placeholder for future API-Football integration; no network calls implemented.",
        "required_inputs": ["api_key", "league", "season"],
        "produces_columns": [*REQUIRED_MATCH_COLUMNS, *OPTIONAL_CONTEXT_COLUMNS],
        "status": "PLACEHOLDER",
    },
    "understat_placeholder": {
        "importer_id": "understat_placeholder",
        "source_type": "api",
        "description": "Placeholder for future Understat-style xG importer; no network calls implemented.",
        "required_inputs": ["league", "season"],
        "produces_columns": [*REQUIRED_MATCH_COLUMNS, *OPTIONAL_XG_COLUMNS],
        "status": "PLACEHOLDER",
    },
    "fbref_xg_csv": {
        "importer_id": "fbref_xg_csv",
        "source_type": "csv",
        "description": "Placeholder for local FBref-style xG CSV parsing; no network calls implemented.",
        "required_inputs": ["csv_path"],
        "produces_columns": ["Date", "HomeTeam", "AwayTeam", "home_xg", "away_xg", *OPTIONAL_CONTEXT_COLUMNS],
        "status": "PLACEHOLDER",
    },
    "understat_xg_csv_placeholder": {
        "importer_id": "understat_xg_csv_placeholder",
        "source_type": "csv/api_placeholder",
        "description": "Placeholder for Understat-style xG CSV/API normalization; no network calls implemented.",
        "required_inputs": ["csv_path"],
        "produces_columns": ["Date", "HomeTeam", "AwayTeam", "home_xg", "away_xg"],
        "status": "PLACEHOLDER",
    },
    "manual_xg_csv": {
        "importer_id": "manual_xg_csv",
        "source_type": "csv",
        "description": "Manually maintained xG enrichment CSV following the Phase 12.6 contract.",
        "required_inputs": ["csv_path"],
        "produces_columns": ["Date", "HomeTeam", "AwayTeam", *OPTIONAL_XG_COLUMNS],
        "status": "ACTIVE",
    },
    "clubelo_placeholder": {
        "importer_id": "clubelo_placeholder",
        "source_type": "api",
        "description": "Placeholder for future ClubElo context importer; no network calls implemented.",
        "required_inputs": ["date", "teams"],
        "produces_columns": ["Date", "HomeTeam", "AwayTeam", "home_elo", "away_elo"],
        "status": "PLACEHOLDER",
    },
}


def list_importers() -> list[dict[str, Any]]:
    return list(IMPORTER_REGISTRY.values())


def get_importer(importer_id: str) -> dict[str, Any] | None:
    return IMPORTER_REGISTRY.get(importer_id)
