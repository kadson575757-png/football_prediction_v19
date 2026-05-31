# -*- coding: utf-8 -*-
"""Partial xG source attribution for Phase 12.7.

Diagnostic/foundation only. No xG values are inferred, invented, deleted, or
modified.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from football_prediction_v19.data_contracts import summarize_data_quality_by_file_type
from football_prediction_v19.xg_enrichment import (
    XG_CONTRACT_MISSING_IDENTITY,
    XG_CONTRACT_MISSING_XG_VALUES,
    XG_CONTRACT_PARTIAL,
    summarize_xg_coverage,
)
from football_prediction_v19.xg_policy import (
    ALLOW_EMPTY_XG_PLACEHOLDERS,
    XG_PLACEHOLDER_EMPTY,
    classify_xg_policy_status,
)

EMPTY_XG_COLUMNS_IN_PROCESSED_FEATURES = "EMPTY_XG_COLUMNS_IN_PROCESSED_FEATURES"
HISTORICAL_MATCHES_MISSING_XG_PAIR = "HISTORICAL_MATCHES_MISSING_XG_PAIR"
FIXTURE_FILE_MISSING_XG_PAIR = "FIXTURE_FILE_MISSING_XG_PAIR"
ODDS_FILE_NOT_XG_SOURCE = "ODDS_FILE_NOT_XG_SOURCE"
FBREF_IDENTITY_MAPPING_MISSING = "FBREF_IDENTITY_MAPPING_MISSING"
UNDERSTAT_IDENTITY_MAPPING_MISSING = "UNDERSTAT_IDENTITY_MAPPING_MISSING"
TEMPLATE_PARTIAL_XG = "TEMPLATE_PARTIAL_XG"
SAMPLE_OR_DEMO_PARTIAL_XG = "SAMPLE_OR_DEMO_PARTIAL_XG"
REAL_XG_SOURCE_WITH_NULL_VALUES = "REAL_XG_SOURCE_WITH_NULL_VALUES"
REAL_XG_SOURCE_WITH_NEGATIVE_VALUES = "REAL_XG_SOURCE_WITH_NEGATIVE_VALUES"
UNKNOWN_PARTIAL_XG_SOURCE = "UNKNOWN_PARTIAL_XG_SOURCE"
NON_BLOCKING_NOT_XG_SOURCE = "NON_BLOCKING_NOT_XG_SOURCE"

NEEDS_MANUAL_XG_VALUES = "NEEDS_MANUAL_XG_VALUES"
NEEDS_XG_COLUMN_CLEANUP_POLICY = "NEEDS_XG_COLUMN_CLEANUP_POLICY"
EMPTY_XG_PLACEHOLDER_ACCEPTED = "EMPTY_XG_PLACEHOLDER_ACCEPTED"
EMPTY_XG_PLACEHOLDER_BLOCKING = "EMPTY_XG_PLACEHOLDER_BLOCKING"
NEEDS_FBREF_MAPPING = "NEEDS_FBREF_MAPPING"
NEEDS_UNDERSTAT_MAPPING = "NEEDS_UNDERSTAT_MAPPING"
IGNORE_TEMPLATE_OR_SAMPLE = "IGNORE_TEMPLATE_OR_SAMPLE"
IGNORE_NON_XG_SOURCE = "IGNORE_NON_XG_SOURCE"
READY_FOR_XG_IMPORTER_SKELETONS = "READY_FOR_XG_IMPORTER_SKELETONS"
MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"

_PARTIAL_LABELS = {
    XG_CONTRACT_PARTIAL,
    XG_CONTRACT_MISSING_IDENTITY,
    XG_CONTRACT_MISSING_XG_VALUES,
}


def _boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def _has_xg_signal(summary: dict[str, Any], path: str | Path) -> bool:
    available = str(summary.get("available_xg_columns", "") or "").strip()
    if available:
        return True
    return "xg" in Path(path).name.lower()


def _xg_columns_all_null(df: pd.DataFrame, xg_summary: dict[str, Any]) -> bool:
    cols = xg_summary.get("available_xg_columns", [])
    if isinstance(cols, str):
        cols = [col.strip() for col in cols.split("|") if col.strip()]
    if not cols:
        return False
    actual = [col for col in cols if col in df.columns]
    if not actual:
        return False
    values = df[actual].apply(pd.to_numeric, errors="coerce")
    return bool(values.isna().all().all())


def _recommended_action(category: str) -> str:
    return {
        EMPTY_XG_COLUMNS_IN_PROCESSED_FEATURES: "allowed placeholder under Phase 12.8 policy; add production xG later via manual_xg_csv/importer",
        HISTORICAL_MATCHES_MISSING_XG_PAIR: "add manual xG enrichment source only if this file is intended as an xG source",
        FIXTURE_FILE_MISSING_XG_PAIR: "ignore for xG unless this fixture file is explicitly intended as an xG source",
        ODDS_FILE_NOT_XG_SOURCE: "ignore for xG enrichment; odds files are not xG sources",
        FBREF_IDENTITY_MAPPING_MISSING: "define FBref identity mapping before xG enrichment use",
        UNDERSTAT_IDENTITY_MAPPING_MISSING: "define Understat identity mapping before xG enrichment use",
        TEMPLATE_PARTIAL_XG: "ignore template/sample artifact for production xG readiness",
        SAMPLE_OR_DEMO_PARTIAL_XG: "ignore template/sample artifact for production xG readiness",
        REAL_XG_SOURCE_WITH_NULL_VALUES: "fill missing xG values from a trusted manual/importer source; do not infer values",
        REAL_XG_SOURCE_WITH_NEGATIVE_VALUES: "review negative xG values manually; do not auto-repair",
        NON_BLOCKING_NOT_XG_SOURCE: "ignore for xG readiness",
    }.get(category, "manual review required")


def _decision_and_blocking(category: str, policy_status: str = "") -> tuple[str, bool]:
    if category == EMPTY_XG_COLUMNS_IN_PROCESSED_FEATURES:
        if policy_status == XG_PLACEHOLDER_EMPTY:
            return EMPTY_XG_PLACEHOLDER_ACCEPTED, False
        return NEEDS_XG_COLUMN_CLEANUP_POLICY, True
    if category == REAL_XG_SOURCE_WITH_NULL_VALUES:
        return NEEDS_MANUAL_XG_VALUES, True
    if category == REAL_XG_SOURCE_WITH_NEGATIVE_VALUES:
        return MANUAL_REVIEW_REQUIRED, True
    if category == FBREF_IDENTITY_MAPPING_MISSING:
        return NEEDS_FBREF_MAPPING, True
    if category == UNDERSTAT_IDENTITY_MAPPING_MISSING:
        return NEEDS_UNDERSTAT_MAPPING, True
    if category in {TEMPLATE_PARTIAL_XG, SAMPLE_OR_DEMO_PARTIAL_XG}:
        return IGNORE_TEMPLATE_OR_SAMPLE, False
    if category in {FIXTURE_FILE_MISSING_XG_PAIR, ODDS_FILE_NOT_XG_SOURCE, NON_BLOCKING_NOT_XG_SOURCE}:
        return IGNORE_NON_XG_SOURCE, False
    if category == HISTORICAL_MATCHES_MISSING_XG_PAIR:
        return IGNORE_NON_XG_SOURCE, False
    return MANUAL_REVIEW_REQUIRED, True


def _fixture_decision(path: Path) -> tuple[str, bool]:
    if "xg" in path.name.lower():
        return NEEDS_MANUAL_XG_VALUES, True
    return IGNORE_NON_XG_SOURCE, False


def classify_partial_xg_source(
    path: str | Path,
    df: pd.DataFrame,
    xg_summary: dict[str, Any] | None = None,
    file_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify why a file is partial for xG enrichment."""
    p = Path(path)
    name = p.name.lower()
    xg_summary = xg_summary or summarize_xg_coverage(df, path=p)
    file_summary = file_summary or summarize_data_quality_by_file_type(p, df)
    policy_status = classify_xg_policy_status(p, df, xg_summary=xg_summary, file_summary=file_summary)
    file_type = str(file_summary.get("file_type", ""))
    adapter_type = str(file_summary.get("adapter_type", ""))
    label = str(xg_summary.get("xg_contract_label", ""))
    has_signal = _has_xg_signal(xg_summary, p)

    if "template" in name:
        category = TEMPLATE_PARTIAL_XG
    elif "sample" in name or "demo" in name:
        category = SAMPLE_OR_DEMO_PARTIAL_XG
    elif int(xg_summary.get("xg_negative_count") or 0) > 0:
        category = REAL_XG_SOURCE_WITH_NEGATIVE_VALUES
    elif "FBREF" in adapter_type.upper() and label == XG_CONTRACT_MISSING_IDENTITY:
        category = FBREF_IDENTITY_MAPPING_MISSING
    elif "understat" in name and label == XG_CONTRACT_MISSING_IDENTITY:
        category = UNDERSTAT_IDENTITY_MAPPING_MISSING
    elif file_type == "PROCESSED_FEATURE_CSV" and _xg_columns_all_null(df, xg_summary):
        category = EMPTY_XG_COLUMNS_IN_PROCESSED_FEATURES
    elif file_type == "FIXTURE_CSV":
        category = FIXTURE_FILE_MISSING_XG_PAIR
    elif file_type == "ODDS_CSV":
        category = ODDS_FILE_NOT_XG_SOURCE
    elif label == XG_CONTRACT_MISSING_XG_VALUES and has_signal:
        category = REAL_XG_SOURCE_WITH_NULL_VALUES
    elif file_type == "HISTORICAL_MATCH_CSV" and not has_signal:
        category = HISTORICAL_MATCHES_MISSING_XG_PAIR
    elif not has_signal:
        category = NON_BLOCKING_NOT_XG_SOURCE
    else:
        category = UNKNOWN_PARTIAL_XG_SOURCE

    if category == FIXTURE_FILE_MISSING_XG_PAIR:
        decision, blocking = _fixture_decision(p)
    else:
        decision, blocking = _decision_and_blocking(category, policy_status=policy_status)
    return {
        "partial_xg_source_category": category,
        "partial_xg_decision": decision,
        "blocking": blocking,
        "xg_policy": ALLOW_EMPTY_XG_PLACEHOLDERS,
        "xg_policy_status": policy_status,
        "xg_usable_for_model": policy_status == "XG_PRODUCTION_READY",
        "xg_placeholder": policy_status == XG_PLACEHOLDER_EMPTY,
        "xg_policy_note": "Empty xG placeholders are accepted but not usable for model features." if policy_status == XG_PLACEHOLDER_EMPTY else "",
        "policy_resolved": category == EMPTY_XG_COLUMNS_IN_PROCESSED_FEATURES and policy_status == XG_PLACEHOLDER_EMPTY,
        "recommended_action": _recommended_action(category),
    }


def build_partial_xg_attribution_for_dataframe(path: str | Path, df: pd.DataFrame) -> dict[str, Any]:
    xg_summary = summarize_xg_coverage(df, path=path)
    file_summary = summarize_data_quality_by_file_type(path, df)
    attribution = classify_partial_xg_source(path, df, xg_summary=xg_summary, file_summary=file_summary)
    return {
        "file_path": str(path),
        "file_name": Path(path).name,
        "file_type": file_summary.get("file_type", ""),
        "xg_schema": xg_summary.get("xg_schema", ""),
        "xg_contract_label": xg_summary.get("xg_contract_label", ""),
        "xg_file_role": xg_summary.get("xg_file_role", ""),
        "row_count": xg_summary.get("row_count", 0),
        "xg_null_count": xg_summary.get("xg_null_count", 0),
        "xg_negative_count": xg_summary.get("xg_negative_count", 0),
        "xg_duplicate_identity_count": xg_summary.get("duplicate_identity_count", 0),
        **attribution,
    }


def build_partial_xg_attribution_for_files(paths: Iterable[str | Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        p = Path(path)
        try:
            df = pd.read_csv(p, low_memory=False)
        except Exception:
            df = pd.DataFrame()
        row = build_partial_xg_attribution_for_dataframe(p, df)
        if row["xg_contract_label"] in _PARTIAL_LABELS or row["xg_file_role"] == "PARTIAL_XG_SOURCE":
            rows.append(row)
    return rows


def summarize_partial_xg_attribution(rows: list[dict[str, Any]]) -> pd.DataFrame:
    table = pd.DataFrame(rows)
    if table.empty:
        return pd.DataFrame(columns=["partial_xg_source_category", "n", "row_count_total", "xg_null_total", "blocking_count", "decision_labels"])
    grouped = table.groupby("partial_xg_source_category", dropna=False)
    out = grouped.agg(
        n=("file_name", "count"),
        row_count_total=("row_count", "sum"),
        xg_null_total=("xg_null_count", "sum"),
        blocking_count=("blocking", "sum"),
    ).reset_index()
    decisions = grouped["partial_xg_decision"].apply(lambda values: " | ".join(sorted(set(map(str, values))))).reset_index(name="decision_labels")
    return out.merge(decisions, on="partial_xg_source_category", how="left")
