# -*- coding: utf-8 -*-
"""Adapter mapping for known non-standard CSV inputs.

Diagnostic/foundation only. No scraping, credentials, network calls, model
probability changes, recommended-market changes, market-tier changes, betting,
staking, or ROI logic.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

FBREF_MATCH_STATS_CSV = "FBREF_MATCH_STATS_CSV"
MLS_MATCHES_CSV = "MLS_MATCHES_CSV"
DAILY_FIXTURE_ANALYSIS_CSV = "DAILY_FIXTURE_ANALYSIS_CSV"
FINAL_SCORES_CSV = "FINAL_SCORES_CSV"
SAMPLE_ANALYSIS_INPUT_CSV = "SAMPLE_ANALYSIS_INPUT_CSV"
UNKNOWN_ADAPTER = "UNKNOWN_ADAPTER"

ADAPTER_READY = "ADAPTER_READY"
ADAPTER_NEEDS_MAPPING = "ADAPTER_NEEDS_MAPPING"
ADAPTER_UNSUPPORTED = "ADAPTER_UNSUPPORTED"
ADAPTER_TEMPLATE_ONLY = "ADAPTER_TEMPLATE_ONLY"

_ADAPTERS: dict[str, dict[str, Any]] = {
    "mls_fbref_raw.csv": {
        "adapter_type": FBREF_MATCH_STATS_CSV,
        "intended_use": "xG/context enrichment",
        "identity_contracts": (
            ("Date", "Home", "Away"),
            ("Date", "Squad", "Opponent"),
            ("date", "home_team", "away_team"),
        ),
        "optional_odds": (),
        "optional_xg": ("xG", "xG.1", "home_xg", "away_xg"),
        "produces": "context/xG/team stats where available",
        "replay_source": False,
        "classification": "ADAPTER_MAPPED_CSV",
    },
    "mls_matches.csv": {
        "adapter_type": MLS_MATCHES_CSV,
        "intended_use": "MLS processed analysis input / enrichment source",
        "identity_contracts": (
            ("date", "home_team", "away_team"),
            ("Date", "HomeTeam", "AwayTeam"),
        ),
        "optional_odds": ("odds_home", "odds_draw", "odds_away", "B365H", "B365D", "B365A"),
        "optional_xg": ("home_xg", "away_xg", "xG_home", "xG_away", "xG", "xG.1"),
        "produces": "processed analysis enrichment columns",
        "replay_source": "full_historical_only",
        "classification": "ADAPTER_MAPPED_CSV",
    },
    "seriea_today.csv": {
        "adapter_type": DAILY_FIXTURE_ANALYSIS_CSV,
        "intended_use": "daily fixture analysis input",
        "identity_contracts": (("date", "home_team", "away_team"),),
        "optional_odds": ("odds_home", "odds_draw", "odds_away"),
        "optional_xg": (),
        "produces": "daily fixture analysis input",
        "replay_source": False,
        "classification": "FIXTURE_CSV",
    },
    "final_scores.csv": {
        "adapter_type": FINAL_SCORES_CSV,
        "intended_use": "post-match score/evaluation input",
        "identity_contracts": (
            ("date", "home_team", "away_team"),
            ("Date", "HomeTeam", "AwayTeam"),
        ),
        "score_contracts": (
            ("home_score", "away_score"),
            ("home_goals", "away_goals"),
            ("FTHG", "FTAG"),
        ),
        "optional_odds": (),
        "optional_xg": (),
        "produces": "post-match score/evaluation input",
        "replay_source": False,
        "classification": "ADAPTER_MAPPED_CSV",
    },
    "sample_matches.csv": {
        "adapter_type": SAMPLE_ANALYSIS_INPUT_CSV,
        "intended_use": "sample/demo analysis input",
        "identity_contracts": (
            ("Date", "Home", "Away"),
            ("date", "home_team", "away_team"),
            ("Date", "HomeTeam", "AwayTeam"),
        ),
        "optional_odds": ("odds_home", "odds_draw", "odds_away", "B365H", "B365D", "B365A"),
        "optional_xg": ("xG", "xG.1", "home_xg", "away_xg", "xG_home", "xG_away"),
        "produces": "sample/demo analysis input",
        "replay_source": "full_historical_only",
        "classification": "ADAPTER_MAPPED_CSV",
    },
}


def _normalize(name: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(name or "").strip().lower())


def _available(columns: list[Any], expected: tuple[str, ...]) -> list[str]:
    by_norm = {_normalize(col): str(col) for col in columns}
    return [by_norm[_normalize(col)] for col in expected if _normalize(col) in by_norm]


def _has_all(columns: list[Any], expected: tuple[str, ...]) -> bool:
    normalized = {_normalize(col) for col in columns}
    return all(_normalize(col) in normalized for col in expected)


def _matching_contract(columns: list[Any], contracts: tuple[tuple[str, ...], ...]) -> tuple[str, ...] | None:
    return next((contract for contract in contracts if _has_all(columns, contract)), None)


def _missing_for_best_contract(columns: list[Any], contracts: tuple[tuple[str, ...], ...]) -> list[str]:
    normalized = {_normalize(col) for col in columns}
    best = min(
        contracts,
        key=lambda contract: sum(1 for col in contract if _normalize(col) not in normalized),
    )
    return [col for col in best if _normalize(col) not in normalized]


def _has_full_historical_contract(columns: list[Any]) -> bool:
    return _has_all(columns, ("Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"))


def get_adapter_mapping_for_file(path: str | Path, columns: list[Any]) -> dict[str, Any] | None:
    """Return a known adapter mapping for ``path`` if one exists."""
    return _ADAPTERS.get(Path(path).name.lower())


def validate_adapter_contract(path: str | Path, df: pd.DataFrame) -> dict[str, Any]:
    columns = list(df.columns)
    mapping = get_adapter_mapping_for_file(path, columns)
    if mapping is None:
        return {
            "adapter_type": UNKNOWN_ADAPTER,
            "adapter_readiness": ADAPTER_UNSUPPORTED,
            "missing_adapter_columns": [],
            "available_identity_columns": [],
            "available_odds_columns": [],
            "available_xg_columns": [],
            "replay_source": False,
            "adapter_note": "No adapter mapping exists for this CSV.",
        }

    identity_contracts = mapping["identity_contracts"]
    matched_identity = _matching_contract(columns, identity_contracts)
    missing = [] if matched_identity else _missing_for_best_contract(columns, identity_contracts)
    score_contracts = mapping.get("score_contracts", ())
    if score_contracts and _matching_contract(columns, score_contracts) is None:
        missing += _missing_for_best_contract(columns, score_contracts)

    replay_source = mapping["replay_source"]
    if replay_source == "full_historical_only":
        replay_source = _has_full_historical_contract(columns)

    readiness = ADAPTER_READY if not missing else ADAPTER_NEEDS_MAPPING
    return {
        "adapter_type": mapping["adapter_type"],
        "adapter_readiness": readiness,
        "missing_adapter_columns": missing,
        "available_identity_columns": list(matched_identity or ()),
        "available_odds_columns": _available(columns, tuple(mapping.get("optional_odds", ()))),
        "available_xg_columns": _available(columns, tuple(mapping.get("optional_xg", ()))),
        "replay_source": bool(replay_source),
        "adapter_note": mapping["produces"] if readiness == ADAPTER_READY else "Adapter mapping exists but required columns are missing.",
    }


def classify_unknown_csv_with_adapter(path: str | Path, columns: list[Any]) -> str:
    """Return an adapter-backed file type for a CSV that would otherwise be unknown."""
    mapping = get_adapter_mapping_for_file(path, columns)
    if mapping is None:
        return "UNKNOWN_CSV"
    if validate_adapter_contract(path, pd.DataFrame(columns=columns))["adapter_readiness"] == ADAPTER_READY:
        return str(mapping["classification"])
    return "ADAPTER_MAPPED_CSV"


def summarize_adapter_mapping(path: str | Path, df: pd.DataFrame) -> dict[str, Any]:
    mapping = get_adapter_mapping_for_file(path, list(df.columns))
    validation = validate_adapter_contract(path, df)
    if mapping is None:
        intended_use = ""
    else:
        intended_use = str(mapping["intended_use"])
    return {
        "adapter_type": validation["adapter_type"],
        "adapter_readiness": validation["adapter_readiness"],
        "intended_use": intended_use,
        "replay_source": validation["replay_source"],
        "missing_adapter_columns": validation["missing_adapter_columns"],
        "available_identity_columns": validation["available_identity_columns"],
        "available_odds_columns": validation["available_odds_columns"],
        "available_xg_columns": validation["available_xg_columns"],
        "adapter_note": validation["adapter_note"],
    }
