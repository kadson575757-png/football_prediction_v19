# -*- coding: utf-8 -*-
"""Fixture-file status policy for Phase 12.4.

Diagnostic/foundation only. This module does not change model probabilities,
recommended-market logic, market-tier rules, betting, staking, or ROI logic.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

FIXTURE_READY = "FIXTURE_READY"
EMPTY_FIXTURE_OK = "EMPTY_FIXTURE_OK"
EMPTY_FIXTURE_NEEDS_REFRESH = "EMPTY_FIXTURE_NEEDS_REFRESH"
FIXTURE_CONTRACT_INVALID = "FIXTURE_CONTRACT_INVALID"
NOT_A_FIXTURE_FILE = "NOT_A_FIXTURE_FILE"

_IDENTITY_COLUMNS = {"date", "hometeam", "awayteam"}


def _normalize_column_name(name: Any) -> str:
    return "".join(ch for ch in str(name or "").strip().lower() if ch.isalnum())


def _has_fixture_identity(df: pd.DataFrame) -> bool:
    normalized = {_normalize_column_name(col) for col in df.columns}
    return _IDENTITY_COLUMNS.issubset(normalized)


def classify_fixture_status(
    path: str | Path,
    df: pd.DataFrame,
    file_type: str | None = None,
    allow_empty_upcoming: bool = True,
) -> str:
    """Classify whether a fixture CSV is ready, allowed empty, or blocking."""
    p = Path(path)
    resolved_file_type = file_type
    if resolved_file_type is None:
        from football_prediction_v19.data_contracts import classify_csv_file

        resolved_file_type = classify_csv_file(p, list(df.columns))

    if resolved_file_type != "FIXTURE_CSV":
        return NOT_A_FIXTURE_FILE

    if len(df) > 0:
        return FIXTURE_READY if _has_fixture_identity(df) else FIXTURE_CONTRACT_INVALID

    if p.name.lower().startswith("upcoming_") and allow_empty_upcoming:
        return EMPTY_FIXTURE_OK
    return EMPTY_FIXTURE_NEEDS_REFRESH


def fixture_status_reason(status: str) -> str:
    reasons = {
        FIXTURE_READY: "Fixture file has rows and required identity columns.",
        EMPTY_FIXTURE_OK: "Empty upcoming fixture file is allowed by policy.",
        EMPTY_FIXTURE_NEEDS_REFRESH: "Empty fixture file should be refreshed or removed if stale.",
        FIXTURE_CONTRACT_INVALID: "Fixture file has rows but is missing required identity columns.",
        NOT_A_FIXTURE_FILE: "File is not classified as a fixture CSV.",
    }
    return reasons.get(status, "Unknown fixture status.")


def is_fixture_status_blocking(status: str) -> bool:
    return status in {EMPTY_FIXTURE_NEEDS_REFRESH, FIXTURE_CONTRACT_INVALID}
