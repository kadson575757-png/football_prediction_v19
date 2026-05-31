# -*- coding: utf-8 -*-
"""Empty xG column policy for Phase 12.8.

Diagnostic/foundation only. No xG values are inferred, invented, deleted, or
modified.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

ALLOW_EMPTY_XG_PLACEHOLDERS = "ALLOW_EMPTY_XG_PLACEHOLDERS"
REQUIRE_PRODUCTION_XG_VALUES = "REQUIRE_PRODUCTION_XG_VALUES"
IGNORE_XG_COLUMNS_IF_EMPTY = "IGNORE_XG_COLUMNS_IF_EMPTY"
MANUAL_REVIEW_XG_POLICY = "MANUAL_REVIEW_XG_POLICY"

XG_PRODUCTION_READY = "XG_PRODUCTION_READY"
XG_PLACEHOLDER_EMPTY = "XG_PLACEHOLDER_EMPTY"
XG_PARTIAL_NULL_VALUES = "XG_PARTIAL_NULL_VALUES"
XG_NOT_PRESENT = "XG_NOT_PRESENT"
XG_TEMPLATE_OR_SAMPLE = "XG_TEMPLATE_OR_SAMPLE"
XG_MAPPING_REQUIRED = "XG_MAPPING_REQUIRED"


def _split_cols(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [part.strip() for part in str(value or "").split("|") if part.strip()]


def _xg_all_null(df: pd.DataFrame, cols: list[str]) -> bool:
    actual = [col for col in cols if col in df.columns]
    if not actual:
        return False
    return bool(df[actual].apply(pd.to_numeric, errors="coerce").isna().all().all())


def classify_xg_policy_status(
    path: str | Path,
    df: pd.DataFrame,
    xg_summary: dict[str, Any] | None = None,
    file_summary: dict[str, Any] | None = None,
) -> str:
    if xg_summary is None:
        from football_prediction_v19.xg_enrichment import summarize_xg_coverage

        xg_summary = summarize_xg_coverage(df, path=path)
    if file_summary is None:
        name = Path(path).name.lower()
        p = str(path).replace("\\", "/").lower()
        if ("_clean" in name or "/processed/" in p) and "template" not in name:
            file_summary = {"file_type": "PROCESSED_FEATURE_CSV"}
        elif name.startswith("upcoming_") or "fixtures" in name:
            file_summary = {"file_type": "FIXTURE_CSV"}
        elif "odds" in name:
            file_summary = {"file_type": "ODDS_CSV"}
        else:
            file_summary = {"file_type": ""}

    if bool(xg_summary.get("xg_production_ready", False)):
        return XG_PRODUCTION_READY
    if str(xg_summary.get("xg_file_role", "")) == "TEMPLATE_OR_SAMPLE":
        return XG_TEMPLATE_OR_SAMPLE
    if str(xg_summary.get("xg_contract_label", "")) == "XG_CONTRACT_MISSING_IDENTITY":
        return XG_MAPPING_REQUIRED

    cols = _split_cols(xg_summary.get("available_xg_columns", []))
    if not cols:
        return XG_NOT_PRESENT
    if str(file_summary.get("file_type", "")) == "PROCESSED_FEATURE_CSV" and _xg_all_null(df, cols):
        return XG_PLACEHOLDER_EMPTY
    if int(xg_summary.get("xg_null_count") or 0) > 0:
        return XG_PARTIAL_NULL_VALUES
    return XG_PARTIAL_NULL_VALUES


def is_xg_usable_for_model(policy_status: str) -> bool:
    return policy_status == XG_PRODUCTION_READY


def is_xg_placeholder(policy_status: str) -> bool:
    return policy_status == XG_PLACEHOLDER_EMPTY


def xg_policy_note(policy_status: str) -> str:
    notes = {
        XG_PRODUCTION_READY: "Production xG values are present and usable for model features.",
        XG_PLACEHOLDER_EMPTY: "Empty xG columns are accepted placeholders; not usable for model features.",
        XG_PARTIAL_NULL_VALUES: "xG columns contain missing values; do not infer or invent values.",
        XG_NOT_PRESENT: "No xG columns are present.",
        XG_TEMPLATE_OR_SAMPLE: "Template/sample xG is not production-ready.",
        XG_MAPPING_REQUIRED: "xG identity mapping is required before enrichment use.",
    }
    return notes.get(policy_status, "Manual xG policy review required.")


def apply_empty_xg_policy_to_summary(
    summary: dict[str, Any],
    policy: str = ALLOW_EMPTY_XG_PLACEHOLDERS,
) -> dict[str, Any]:
    out = summary.copy()
    status = str(out.get("xg_policy_status", XG_NOT_PRESENT))
    out["xg_policy"] = policy
    out["xg_usable_for_model"] = is_xg_usable_for_model(status)
    out["xg_placeholder"] = is_xg_placeholder(status)
    out["xg_policy_note"] = xg_policy_note(status)
    out["xg_policy_blocking"] = status == XG_PLACEHOLDER_EMPTY and policy == REQUIRE_PRODUCTION_XG_VALUES
    return out
