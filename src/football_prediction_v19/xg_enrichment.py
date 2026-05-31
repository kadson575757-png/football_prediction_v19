# -*- coding: utf-8 -*-
"""xG enrichment contract helpers for Phase 12.6.

Diagnostic/foundation only. No xG values are inferred or invented.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

MATCH_XG_PAIR = "MATCH_XG_PAIR"
TEAM_MATCH_XG_LONG = "TEAM_MATCH_XG_LONG"
FBREF_XG_EXPORT = "FBREF_XG_EXPORT"
UNDERSTAT_XG_EXPORT = "UNDERSTAT_XG_EXPORT"
UNKNOWN_XG_SCHEMA = "UNKNOWN_XG_SCHEMA"

XG_CONTRACT_READY = "XG_CONTRACT_READY"
XG_CONTRACT_PARTIAL = "XG_CONTRACT_PARTIAL"
XG_CONTRACT_MISSING_IDENTITY = "XG_CONTRACT_MISSING_IDENTITY"
XG_CONTRACT_MISSING_XG_VALUES = "XG_CONTRACT_MISSING_XG_VALUES"
XG_CONTRACT_UNSUPPORTED = "XG_CONTRACT_UNSUPPORTED"
XG_CONTRACT_EMPTY = "XG_CONTRACT_EMPTY"

TEMPLATE_OR_SAMPLE = "TEMPLATE_OR_SAMPLE"
PRODUCTION_XG_SOURCE = "PRODUCTION_XG_SOURCE"
PARTIAL_XG_SOURCE = "PARTIAL_XG_SOURCE"
NON_XG_SOURCE = "NON_XG_SOURCE"

_MATCH_IDENTITIES = (
    ("Date", "HomeTeam", "AwayTeam"),
    ("date", "home_team", "away_team"),
)
_MATCH_XG_PAIRS = (
    ("home_xg", "away_xg"),
    ("xG_home", "xG_away"),
    ("hxg", "axg"),
)
_TEAM_LONG_REQUIRED = ("date", "team", "opponent", "xg", "xga")
_FBREF_REQUIRED = ("Date", "Squad", "Opponent", "xG", "xGA")
_UNDERSTAT_IDENTITIES = (("date", "home_team", "away_team"),)
_UNDERSTAT_XG_PAIRS = (("home_xG", "away_xG"), ("h_xg", "a_xg"))


def _normalize(name: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(name or "").strip().lower())


def _by_norm(columns: list[Any]) -> dict[str, str]:
    return {_normalize(col): str(col) for col in columns}


def _has_all(columns: list[Any], expected: tuple[str, ...]) -> bool:
    normalized = set(_by_norm(columns))
    return all(_normalize(col) in normalized for col in expected)


def _available(columns: list[Any], expected: tuple[str, ...]) -> list[str]:
    by_norm = _by_norm(columns)
    return [by_norm[_normalize(col)] for col in expected if _normalize(col) in by_norm]


def _matching_contract(columns: list[Any], contracts: tuple[tuple[str, ...], ...]) -> tuple[str, ...] | None:
    return next((contract for contract in contracts if _has_all(columns, contract)), None)


def _matching_exact_contract(columns: list[Any], contracts: tuple[tuple[str, ...], ...]) -> tuple[str, ...] | None:
    available = {str(col) for col in columns}
    return next((contract for contract in contracts if all(col in available for col in contract)), None)


def _best_missing(columns: list[Any], contracts: tuple[tuple[str, ...], ...]) -> list[str]:
    normalized = set(_by_norm(columns))
    best = min(contracts, key=lambda contract: sum(_normalize(col) not in normalized for col in contract))
    return [col for col in best if _normalize(col) not in normalized]


def detect_xg_schema(columns: list[Any]) -> str:
    """Detect the xG schema family represented by ``columns``."""
    cols = list(columns)
    if _has_all(cols, _FBREF_REQUIRED):
        return FBREF_XG_EXPORT
    if _has_all(cols, _TEAM_LONG_REQUIRED):
        return TEAM_MATCH_XG_LONG
    if _matching_contract(cols, _UNDERSTAT_IDENTITIES) and _matching_exact_contract(cols, _UNDERSTAT_XG_PAIRS):
        return UNDERSTAT_XG_EXPORT
    if _matching_contract(cols, _MATCH_IDENTITIES) and _matching_contract(cols, _MATCH_XG_PAIRS):
        return MATCH_XG_PAIR
    has_identity = bool(
        _matching_contract(cols, _MATCH_IDENTITIES)
        or _has_all(cols, ("date", "team", "opponent"))
        or _has_all(cols, ("Date", "Squad", "Opponent"))
        or _matching_contract(cols, _UNDERSTAT_IDENTITIES)
    )
    has_xg = bool(
        _matching_contract(cols, _MATCH_XG_PAIRS)
        or _has_all(cols, ("xg", "xga"))
        or _has_all(cols, ("xG", "xGA"))
        or _matching_exact_contract(cols, _UNDERSTAT_XG_PAIRS)
    )
    return XG_CONTRACT_PARTIAL if has_identity or has_xg else UNKNOWN_XG_SCHEMA


def get_xg_identity_columns(columns: list[Any]) -> list[str]:
    cols = list(columns)
    contracts = (
        *_MATCH_IDENTITIES,
        ("date", "team", "opponent"),
        ("Date", "Squad", "Opponent"),
        *_UNDERSTAT_IDENTITIES,
    )
    match = _matching_contract(cols, contracts)
    return list(match or ())


def get_xg_value_columns(columns: list[Any]) -> list[str]:
    cols = list(columns)
    contracts = (
        *_MATCH_XG_PAIRS,
        ("xg", "xga"),
        ("xG", "xGA"),
        *_UNDERSTAT_XG_PAIRS,
    )
    match = _matching_contract(cols, contracts)
    return list(match or ())


def _missing_identity(columns: list[Any]) -> list[str]:
    if get_xg_identity_columns(columns):
        return []
    contracts = (
        *_MATCH_IDENTITIES,
        ("date", "team", "opponent"),
        ("Date", "Squad", "Opponent"),
        *_UNDERSTAT_IDENTITIES,
    )
    return _best_missing(columns, contracts)


def _missing_xg(columns: list[Any]) -> list[str]:
    if get_xg_value_columns(columns):
        return []
    contracts = (*_MATCH_XG_PAIRS, ("xg", "xga"), ("xG", "xGA"), *_UNDERSTAT_XG_PAIRS)
    return _best_missing(columns, contracts)


def _count_duplicate_identity(df: pd.DataFrame, identity_cols: list[str]) -> int:
    if not identity_cols:
        return 0
    actual = []
    by_norm = _by_norm(list(df.columns))
    for col in identity_cols:
        actual_col = by_norm.get(_normalize(col))
        if actual_col is not None:
            actual.append(actual_col)
    if len(actual) != len(identity_cols):
        return 0
    return int(df.duplicated(subset=actual, keep="first").sum())


def _xg_frame(df: pd.DataFrame, xg_cols: list[str]) -> pd.DataFrame:
    by_norm = _by_norm(list(df.columns))
    actual = [by_norm[_normalize(col)] for col in xg_cols if _normalize(col) in by_norm]
    if not actual:
        return pd.DataFrame(index=df.index)
    return df[actual].apply(pd.to_numeric, errors="coerce")


def _is_template_or_sample(path: str | Path | None, row_count: int) -> bool:
    name = Path(str(path or "")).name.lower()
    if "template" in name or "sample" in name:
        return True
    demo_markers = ("demo", "example", "from_template", "xg_clean", "xg_raw")
    return row_count <= 3 and any(marker in name for marker in demo_markers)


def _xg_file_role(path: str | Path | None, label: str, row_count: int) -> str:
    if label == XG_CONTRACT_READY:
        if _is_template_or_sample(path, row_count):
            return TEMPLATE_OR_SAMPLE
        return PRODUCTION_XG_SOURCE
    if label in {XG_CONTRACT_PARTIAL, XG_CONTRACT_MISSING_IDENTITY, XG_CONTRACT_MISSING_XG_VALUES}:
        return PARTIAL_XG_SOURCE
    return NON_XG_SOURCE


def validate_xg_dataframe(df: pd.DataFrame, path: str | Path | None = None) -> dict[str, Any]:
    """Validate a dataframe against Phase 12.6 xG enrichment contracts."""
    columns = list(df.columns)
    row_count = int(len(df))
    schema = detect_xg_schema(columns)
    identity_cols = get_xg_identity_columns(columns)
    xg_cols = get_xg_value_columns(columns)
    missing_identity = _missing_identity(columns)
    missing_xg = _missing_xg(columns)
    xg_values = _xg_frame(df, xg_cols)
    xg_null_count = int(xg_values.isna().sum().sum()) if not xg_values.empty else 0
    xg_negative_count = int((xg_values < 0).sum().sum()) if not xg_values.empty else 0
    duplicate_identity_count = _count_duplicate_identity(df, identity_cols)

    if row_count == 0:
        label = XG_CONTRACT_EMPTY
    elif missing_identity:
        label = XG_CONTRACT_MISSING_IDENTITY
    elif missing_xg or xg_null_count:
        label = XG_CONTRACT_MISSING_XG_VALUES
    elif schema in {UNKNOWN_XG_SCHEMA, XG_CONTRACT_PARTIAL}:
        label = XG_CONTRACT_UNSUPPORTED
    elif xg_negative_count:
        label = XG_CONTRACT_PARTIAL
    else:
        label = XG_CONTRACT_READY

    contract_ready = label == XG_CONTRACT_READY
    role = _xg_file_role(path, label, row_count)
    production_ready = (
        contract_ready
        and role == PRODUCTION_XG_SOURCE
        and row_count > 3
        and xg_null_count == 0
        and xg_negative_count == 0
    )
    recommendation = (
        "ready for xG CSV importer"
        if production_ready
        else "provide identity columns and non-null non-negative xG values following Phase 12.6 contract"
    )
    return {
        "xg_schema": schema,
        "xg_contract_label": label,
        "row_count": row_count,
        "available_identity_columns": identity_cols,
        "available_xg_columns": xg_cols,
        "missing_identity_columns": missing_identity,
        "missing_xg_columns": missing_xg,
        "xg_null_count": xg_null_count,
        "xg_negative_count": xg_negative_count,
        "duplicate_identity_count": duplicate_identity_count,
        "supported_for_enrichment": production_ready,
        "xg_contract_ready": contract_ready,
        "xg_production_ready": production_ready,
        "xg_file_role": role,
        "recommendation": recommendation,
    }


def summarize_xg_coverage(
    df: pd.DataFrame,
    path: str | Path | None = None,
    league: str | None = None,
    season: str | None = None,
) -> dict[str, Any]:
    summary = validate_xg_dataframe(df, path=path)
    summary["league"] = league or ""
    summary["season"] = season or ""
    return summary


def normalize_xg_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with common xG column names normalized."""
    rename = {
        "xghome": "home_xg",
        "homexg": "home_xg",
        "hxg": "home_xg",
        "home_xg": "home_xg",
        "awayxg": "away_xg",
        "xgaway": "away_xg",
        "axg": "away_xg",
        "away_xg": "away_xg",
        "xg": "xg",
        "xga": "xga",
    }
    out = df.copy()
    out.columns = [rename.get(_normalize(col), str(col)) for col in out.columns]
    return out
