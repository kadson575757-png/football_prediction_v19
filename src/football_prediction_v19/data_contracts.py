# -*- coding: utf-8 -*-
"""Input data contracts and data-quality helpers.

Diagnostic/foundation only. This module does not change model probabilities,
recommended-market logic, market-tier rules, betting, staking, or ROI logic.
"""
from __future__ import annotations

import re
import warnings
from pathlib import Path
from typing import Any

import pandas as pd

from football_prediction_v19.csv_adapter_mapping import (
    ADAPTER_NEEDS_MAPPING,
    ADAPTER_READY,
    classify_unknown_csv_with_adapter,
    summarize_adapter_mapping,
)
from football_prediction_v19.fixture_policy import (
    EMPTY_FIXTURE_OK,
    classify_fixture_status,
    fixture_status_reason,
    is_fixture_status_blocking,
)
from football_prediction_v19.xg_enrichment import (
    XG_CONTRACT_MISSING_IDENTITY,
    XG_CONTRACT_MISSING_XG_VALUES,
    XG_CONTRACT_READY,
    summarize_xg_coverage,
)

REQUIRED_MATCH_COLUMNS = (
    "Date",
    "HomeTeam",
    "AwayTeam",
    "FTHG",
    "FTAG",
    "FTR",
)

OPTIONAL_ODDS_COLUMNS = (
    "B365H",
    "B365D",
    "B365A",
    "odds_home",
    "odds_draw",
    "odds_away",
)

OPTIONAL_XG_COLUMNS = (
    "home_xg",
    "away_xg",
    "xG_home",
    "xG_away",
    "hxg",
    "axg",
)

OPTIONAL_CONTEXT_COLUMNS = (
    "league",
    "season",
    "matchday",
    "venue",
    "home_elo",
    "away_elo",
    "rest_days_home",
    "rest_days_away",
)

QUALITY_LABELS = (
    "READY_FOR_REPLAY",
    "READY_WITH_WARNINGS",
    "MISSING_REQUIRED_COLUMNS",
    "EMPTY_DATA",
    "EMPTY_FIXTURE_OK",
    "INVALID_DATA",
    "TEMPLATE_ONLY",
    "READY_FOR_FIXTURES",
    "READY_FOR_ODDS_ENRICHMENT",
    "READY_FOR_XG_ENRICHMENT",
    "PROCESSED_FEATURE_READY",
    "ADAPTER_READY",
    "ADAPTER_NEEDS_MAPPING",
    "XG_CONTRACT_READY",
)

FILE_TYPE_LABELS = (
    "HISTORICAL_MATCH_CSV",
    "FIXTURE_CSV",
    "ODDS_CSV",
    "XG_CSV",
    "TEMPLATE_CSV",
    "PROCESSED_FEATURE_CSV",
    "DIAGNOSTIC_OUTPUT_CSV",
    "ADAPTER_MAPPED_CSV",
    "UNKNOWN_CSV",
)

IDENTITY_CONTRACTS = (
    ("Date", "HomeTeam", "AwayTeam"),
    ("date", "home_team", "away_team"),
)

ODDS_TRIPLETS = (
    ("B365H", "B365D", "B365A"),
    ("odds_home", "odds_draw", "odds_away"),
)

XG_PAIRS = (
    ("home_xg", "away_xg"),
    ("xG_home", "xG_away"),
    ("hxg", "axg"),
)


def normalize_column_name(name: Any) -> str:
    """Return a stable normalized column key for contract matching."""
    return re.sub(r"[^a-z0-9]+", "", str(name or "").strip().lower())


def _available(columns: list[Any], expected: tuple[str, ...]) -> list[str]:
    by_norm = {normalize_column_name(col): str(col) for col in columns}
    found = []
    for col in expected:
        match = by_norm.get(normalize_column_name(col))
        if match is not None:
            found.append(match)
    return found


def detect_column_family(columns: list[Any]) -> dict[str, list[str]]:
    """Detect required and optional column families from a column list."""
    cols = list(columns)
    return {
        "required": _available(cols, REQUIRED_MATCH_COLUMNS),
        "odds": _available(cols, OPTIONAL_ODDS_COLUMNS),
        "xg": _available(cols, OPTIONAL_XG_COLUMNS),
        "context": _available(cols, OPTIONAL_CONTEXT_COLUMNS),
    }


def _norm_set(columns: list[Any]) -> set[str]:
    return {normalize_column_name(col) for col in columns}


def _has_all(columns: list[Any], expected: tuple[str, ...]) -> bool:
    normalized = _norm_set(columns)
    return all(normalize_column_name(col) in normalized for col in expected)


def _has_any_identity(columns: list[Any]) -> bool:
    return any(_has_all(columns, contract) for contract in IDENTITY_CONTRACTS)


def _matching_contract(columns: list[Any], contracts: tuple[tuple[str, ...], ...]) -> tuple[str, ...] | None:
    for contract in contracts:
        if _has_all(columns, contract):
            return contract
    return None


def _missing_for_contract(columns: list[Any], contract: tuple[str, ...]) -> list[str]:
    normalized = _norm_set(columns)
    return [col for col in contract if normalize_column_name(col) not in normalized]


def classify_csv_file(path: str | Any, columns: list[Any]) -> str:
    """Classify a CSV before choosing a validation contract."""
    path_obj = Path(str(path))
    p = str(path_obj).replace("\\", "/").lower()
    name = path_obj.name.lower()
    stem = name.rsplit(".", 1)[0]
    has_scores = _has_all(columns, ("FTHG", "FTAG", "FTR"))
    has_full_historical = _has_all(columns, REQUIRED_MATCH_COLUMNS)

    if "outputs" in p or "diagnostics" in p:
        return "DIAGNOSTIC_OUTPUT_CSV"
    if "template" in name:
        return "TEMPLATE_CSV"
    if name.startswith("upcoming_") or "fixtures" in name:
        return "FIXTURE_CSV"
    if ("_clean" in stem or "/processed/" in p) and not has_full_historical:
        return "PROCESSED_FEATURE_CSV"
    if "odds" in name and not has_scores:
        return "ODDS_CSV"
    if "xg" in name and not has_scores:
        return "XG_CSV"
    if has_full_historical:
        return "HISTORICAL_MATCH_CSV"
    return classify_unknown_csv_with_adapter(path_obj, columns)


def get_contract_for_file_type(file_type: str) -> dict[str, Any]:
    contracts: dict[str, dict[str, Any]] = {
        "HISTORICAL_MATCH_CSV": {
            "contract_type": "historical_match",
            "required": REQUIRED_MATCH_COLUMNS,
        },
        "FIXTURE_CSV": {
            "contract_type": "fixture",
            "identity_contracts": IDENTITY_CONTRACTS,
        },
        "ODDS_CSV": {
            "contract_type": "odds",
            "identity_contracts": IDENTITY_CONTRACTS,
            "triplets": ODDS_TRIPLETS,
        },
        "XG_CSV": {
            "contract_type": "xg",
            "identity_contracts": IDENTITY_CONTRACTS,
            "pairs": XG_PAIRS,
        },
        "TEMPLATE_CSV": {"contract_type": "template"},
        "PROCESSED_FEATURE_CSV": {"contract_type": "processed_feature"},
        "DIAGNOSTIC_OUTPUT_CSV": {"contract_type": "diagnostic_output"},
        "ADAPTER_MAPPED_CSV": {"contract_type": "adapter_mapped"},
        "UNKNOWN_CSV": {"contract_type": "unknown"},
    }
    return contracts.get(file_type, contracts["UNKNOWN_CSV"])


def _col(df: pd.DataFrame, canonical: str) -> str | None:
    norm = normalize_column_name(canonical)
    for col in df.columns:
        if normalize_column_name(col) == norm:
            return str(col)
    return None


def _count_invalid_scores(df: pd.DataFrame) -> int:
    fthg = _col(df, "FTHG")
    ftag = _col(df, "FTAG")
    if not fthg or not ftag:
        return 0
    home = pd.to_numeric(df[fthg], errors="coerce")
    away = pd.to_numeric(df[ftag], errors="coerce")
    return int((home.isna() | away.isna() | (home < 0) | (away < 0)).sum())


def _count_invalid_results(df: pd.DataFrame) -> int:
    ftr = _col(df, "FTR")
    if not ftr:
        return 0
    valid = {"H", "D", "A"}
    invalid = ~df[ftr].astype(str).str.strip().str.upper().isin(valid)
    return int(invalid.sum())


def _count_date_failures(df: pd.DataFrame) -> int:
    date = _col(df, "Date")
    if not date:
        return 0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        parsed = pd.to_datetime(df[date], errors="coerce")
    return int(parsed.isna().sum())


def _count_blank_teams(df: pd.DataFrame) -> int:
    home = _col(df, "HomeTeam")
    away = _col(df, "AwayTeam")
    if not home or not away:
        return 0
    home_blank = df[home].isna() | df[home].astype(str).str.strip().eq("")
    away_blank = df[away].isna() | df[away].astype(str).str.strip().eq("")
    return int((home_blank | away_blank).sum())


def _count_duplicates(df: pd.DataFrame) -> int:
    keys = [_col(df, col) for col in ("Date", "HomeTeam", "AwayTeam")]
    if any(key is None for key in keys):
        return 0
    return int(df.duplicated(subset=[str(key) for key in keys], keep="first").sum())


def validate_match_dataframe(
    df: pd.DataFrame,
    league: str | None = None,
    season: str | None = None,
) -> dict[str, Any]:
    """Validate a match dataframe against the Phase 12.1 input contract."""
    families = detect_column_family(list(df.columns))
    missing = [
        col for col in REQUIRED_MATCH_COLUMNS
        if normalize_column_name(col) not in {normalize_column_name(x) for x in families["required"]}
    ]
    row_count = int(len(df))
    invalid_score_count = _count_invalid_scores(df)
    invalid_result_count = _count_invalid_results(df)
    date_parse_failure_count = _count_date_failures(df)
    team_name_blank_count = _count_blank_teams(df)
    duplicate_match_count = _count_duplicates(df)

    if row_count == 0:
        quality = "EMPTY_DATA"
    elif missing:
        quality = "MISSING_REQUIRED_COLUMNS"
    elif any((
        invalid_score_count,
        invalid_result_count,
        date_parse_failure_count,
        team_name_blank_count,
    )):
        quality = "INVALID_DATA"
    elif not families["odds"] and not families["xg"]:
        quality = "READY_WITH_WARNINGS"
    else:
        quality = "READY_FOR_REPLAY"

    return {
        "league": league or "",
        "season": season or "",
        "missing_required_columns": missing,
        "available_required_columns": families["required"],
        "available_odds_columns": families["odds"],
        "available_xg_columns": families["xg"],
        "available_context_columns": families["context"],
        "row_count": row_count,
        "duplicate_match_count": duplicate_match_count,
        "invalid_score_count": invalid_score_count,
        "invalid_result_count": invalid_result_count,
        "date_parse_failure_count": date_parse_failure_count,
        "team_name_blank_count": team_name_blank_count,
        "quality_label": quality,
    }


def _base_quality_fields(
    df: pd.DataFrame,
    league: str | None,
    season: str | None,
) -> dict[str, Any]:
    families = detect_column_family(list(df.columns))
    return {
        "league": league or "",
        "season": season or "",
        "available_required_columns": families["required"],
        "available_odds_columns": families["odds"],
        "available_xg_columns": families["xg"],
        "available_context_columns": families["context"],
        "row_count": int(len(df)),
        "duplicate_match_count": _count_duplicates(df),
        "invalid_score_count": _count_invalid_scores(df),
        "invalid_result_count": _count_invalid_results(df),
        "date_parse_failure_count": _count_date_failures(df),
        "team_name_blank_count": _count_blank_teams(df),
    }


def _identity_missing(columns: list[Any]) -> list[str]:
    if _has_any_identity(columns):
        return []
    return list(IDENTITY_CONTRACTS[0])


def _quality_for_common_counts(base: dict[str, Any], missing: list[str], ready_label: str) -> str:
    if base["row_count"] == 0:
        return "EMPTY_DATA"
    if missing:
        return "MISSING_REQUIRED_COLUMNS"
    if base["date_parse_failure_count"] or base["team_name_blank_count"]:
        return "INVALID_DATA"
    return ready_label


def validate_dataframe_for_file_type(
    df: pd.DataFrame,
    file_type: str,
    league: str | None = None,
    season: str | None = None,
    path: str | Any | None = None,
    allow_empty_upcoming: bool = True,
) -> dict[str, Any]:
    """Validate a dataframe using the contract implied by ``file_type``."""
    columns = list(df.columns)
    contract = get_contract_for_file_type(file_type)
    base = _base_quality_fields(df, league, season)
    missing: list[str] = []
    label = "READY_WITH_WARNINGS"

    if file_type == "TEMPLATE_CSV":
        label = "TEMPLATE_ONLY"
    elif file_type == "DIAGNOSTIC_OUTPUT_CSV":
        label = "PROCESSED_FEATURE_READY" if base["row_count"] else "EMPTY_DATA"
    elif file_type == "PROCESSED_FEATURE_CSV":
        label = "PROCESSED_FEATURE_READY" if base["row_count"] else "EMPTY_DATA"
    elif file_type == "HISTORICAL_MATCH_CSV":
        result = validate_match_dataframe(df, league=league, season=season)
        result["file_type"] = file_type
        result["contract_type"] = contract["contract_type"]
        result["contract_quality_label"] = result["quality_label"]
        result["missing_contract_columns"] = result["missing_required_columns"]
        return result
    elif file_type == "FIXTURE_CSV":
        missing = _identity_missing(columns)
        status = classify_fixture_status(
            path or "",
            df,
            file_type=file_type,
            allow_empty_upcoming=allow_empty_upcoming,
        )
        if status == EMPTY_FIXTURE_OK:
            label = EMPTY_FIXTURE_OK
        else:
            label = _quality_for_common_counts(base, missing, "READY_FOR_FIXTURES")
    elif file_type == "ODDS_CSV":
        missing = _identity_missing(columns)
        if not _matching_contract(columns, ODDS_TRIPLETS):
            missing += list(ODDS_TRIPLETS[0])
        label = _quality_for_common_counts(base, missing, "READY_FOR_ODDS_ENRICHMENT")
    elif file_type == "XG_CSV":
        xg_summary = summarize_xg_coverage(df, path=path or "")
        missing = list(xg_summary.get("missing_identity_columns", [])) + list(xg_summary.get("missing_xg_columns", []))
        if xg_summary["xg_contract_label"] == XG_CONTRACT_READY:
            label = "READY_FOR_XG_ENRICHMENT"
        elif xg_summary["xg_contract_label"] in {XG_CONTRACT_MISSING_IDENTITY, XG_CONTRACT_MISSING_XG_VALUES}:
            label = "MISSING_REQUIRED_COLUMNS"
        else:
            label = _quality_for_common_counts(base, missing, "READY_FOR_XG_ENRICHMENT")
    elif file_type == "ADAPTER_MAPPED_CSV":
        adapter = summarize_adapter_mapping(path or "", df)
        missing = list(adapter.get("missing_adapter_columns", []))
        label = ADAPTER_READY if adapter.get("adapter_readiness") == ADAPTER_READY else ADAPTER_NEEDS_MAPPING
    else:
        missing = _identity_missing(columns)
        label = "UNKNOWN_CSV" if base["row_count"] else "EMPTY_DATA"

    result = {
        **base,
        "file_type": file_type,
        "contract_type": contract["contract_type"],
        "missing_required_columns": missing,
        "missing_contract_columns": missing,
        "quality_label": label,
        "contract_quality_label": label,
    }
    if file_type == "FIXTURE_CSV":
        status = classify_fixture_status(
            path or "",
            df,
            file_type=file_type,
            allow_empty_upcoming=allow_empty_upcoming,
        )
        result["fixture_status"] = status
        result["fixture_status_reason"] = fixture_status_reason(status)
        result["fixture_status_blocking"] = is_fixture_status_blocking(status)
    if file_type in {"XG_CSV", "ADAPTER_MAPPED_CSV"}:
        xg_summary = summarize_xg_coverage(df, path=path or "")
        result["xg_schema"] = xg_summary["xg_schema"]
        result["xg_contract_label"] = xg_summary["xg_contract_label"]
        result["xg_supported_for_enrichment"] = xg_summary["supported_for_enrichment"]
        result["xg_contract_ready"] = xg_summary["xg_contract_ready"]
        result["xg_production_ready"] = xg_summary["xg_production_ready"]
        result["xg_file_role"] = xg_summary["xg_file_role"]
        result["xg_null_count"] = xg_summary["xg_null_count"]
        result["xg_negative_count"] = xg_summary["xg_negative_count"]
        result["xg_duplicate_identity_count"] = xg_summary["duplicate_identity_count"]
    return result


def summarize_data_quality_by_file_type(
    path: str | Any,
    df: pd.DataFrame,
    league: str | None = None,
    season: str | None = None,
) -> dict[str, Any]:
    """Classify a CSV path and return a friendly contract-specific summary."""
    file_type = classify_csv_file(path, list(df.columns))
    result = validate_dataframe_for_file_type(df, file_type, league=league, season=season, path=path)
    out = result.copy()
    out["file_type"] = file_type
    out["contract_type"] = result.get("contract_type", get_contract_for_file_type(file_type)["contract_type"])
    out["contract_quality_label"] = result.get("contract_quality_label", result.get("quality_label", ""))
    out["replay_ready"] = out["contract_quality_label"] == "READY_FOR_REPLAY"
    out["fixture_ready"] = out["contract_quality_label"] == "READY_FOR_FIXTURES"
    out.setdefault("fixture_status", "NOT_A_FIXTURE_FILE")
    out.setdefault("fixture_status_reason", "File is not classified as a fixture CSV.")
    out.setdefault("fixture_status_blocking", False)
    out["odds_ready"] = out["contract_quality_label"] == "READY_FOR_ODDS_ENRICHMENT"
    xg_summary = summarize_xg_coverage(df, path=path)
    out.setdefault("xg_schema", xg_summary["xg_schema"])
    out.setdefault("xg_contract_label", xg_summary["xg_contract_label"])
    out.setdefault("xg_supported_for_enrichment", xg_summary["supported_for_enrichment"])
    out.setdefault("xg_contract_ready", xg_summary["xg_contract_ready"])
    out.setdefault("xg_production_ready", xg_summary["xg_production_ready"])
    out.setdefault("xg_file_role", xg_summary["xg_file_role"])
    out.setdefault("xg_null_count", xg_summary["xg_null_count"])
    out.setdefault("xg_negative_count", xg_summary["xg_negative_count"])
    out.setdefault("xg_duplicate_identity_count", xg_summary["duplicate_identity_count"])
    out["xg_ready"] = (
        out["contract_quality_label"] == "READY_FOR_XG_ENRICHMENT"
        and bool(out.get("xg_production_ready", False))
    )
    out["template_only"] = out["contract_quality_label"] == "TEMPLATE_ONLY"
    out["processed_feature_ready"] = out["contract_quality_label"] == "PROCESSED_FEATURE_READY"
    adapter = summarize_adapter_mapping(path, df)
    out["adapter_type"] = adapter["adapter_type"]
    out["adapter_readiness"] = adapter["adapter_readiness"]
    out["intended_use"] = adapter["intended_use"]
    out["replay_source"] = adapter["replay_source"]
    out["missing_adapter_columns"] = adapter["missing_adapter_columns"]
    out["available_adapter_identity_columns"] = adapter["available_identity_columns"]
    out["available_adapter_odds_columns"] = adapter["available_odds_columns"]
    out["available_adapter_xg_columns"] = adapter["available_xg_columns"]
    out["adapter_note"] = adapter["adapter_note"]
    for key in (
        "missing_required_columns",
        "missing_contract_columns",
        "available_required_columns",
        "available_odds_columns",
        "available_xg_columns",
        "available_context_columns",
        "missing_adapter_columns",
        "available_adapter_identity_columns",
        "available_adapter_odds_columns",
        "available_adapter_xg_columns",
    ):
        value = out.get(key, [])
        if isinstance(value, list):
            out[key] = " | ".join(value)
    return out


def summarize_data_quality(
    df: pd.DataFrame,
    league: str | None = None,
    season: str | None = None,
) -> dict[str, Any]:
    """Return a CSV/Markdown-friendly data-quality summary."""
    result = validate_match_dataframe(df, league=league, season=season)
    out = result.copy()
    for key in (
        "missing_required_columns",
        "available_required_columns",
        "available_odds_columns",
        "available_xg_columns",
        "available_context_columns",
    ):
        out[key] = " | ".join(result[key])
    return out
