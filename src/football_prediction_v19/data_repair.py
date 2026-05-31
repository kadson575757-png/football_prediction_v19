# -*- coding: utf-8 -*-
"""Safe data-contract repair planning helpers.

Diagnostic/foundation only. Repair previews are copies under
``outputs/repair_preview`` and source CSV files are never modified in place.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from football_prediction_v19.data_contracts import (
    summarize_data_quality_by_file_type,
)


@dataclass(frozen=True)
class RepairAction:
    file_path: str
    file_name: str
    file_type: str
    contract_quality_label: str
    issue_category: str
    issue_detail: str
    recommended_action: str
    auto_repair_supported: bool
    preview_output_path: str
    risk_level: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def safe_preview_output_path(
    source_path: str | Path,
    output_dir: str | Path = "outputs/repair_preview",
) -> Path:
    """Return a non-source preview path under ``output_dir``."""
    source = Path(source_path)
    safe_name = str(source).replace(":", "").replace("\\", "__").replace("/", "__")
    if not safe_name.lower().endswith(".csv"):
        safe_name += ".csv"
    preview = Path(output_dir) / safe_name
    if preview.resolve() == source.resolve():
        preview = Path(output_dir) / f"preview__{source.name}"
    return preview


def _action(
    path: Path,
    summary: dict[str, Any],
    issue_category: str,
    issue_detail: str,
    recommended_action: str,
    risk_level: str,
    auto_repair_supported: bool = False,
) -> RepairAction:
    preview = safe_preview_output_path(path)
    return RepairAction(
        file_path=str(path),
        file_name=path.name,
        file_type=str(summary.get("file_type", "")),
        contract_quality_label=str(summary.get("contract_quality_label", "")),
        issue_category=issue_category,
        issue_detail=issue_detail,
        recommended_action=recommended_action,
        auto_repair_supported=auto_repair_supported,
        preview_output_path=str(preview),
        risk_level=risk_level,
    )


def build_repair_plan_for_dataframe(
    path: str | Path,
    df: pd.DataFrame,
    summary: dict[str, Any] | None = None,
) -> list[RepairAction]:
    """Build zero or more repair-plan actions for one dataframe."""
    p = Path(path)
    summary = summary or summarize_data_quality_by_file_type(p, df)
    file_type = str(summary.get("file_type", "UNKNOWN_CSV"))
    label = str(summary.get("contract_quality_label", ""))
    actions: list[RepairAction] = []

    if file_type == "HISTORICAL_MATCH_CSV":
        if int(summary.get("invalid_score_count") or 0) > 0:
            actions.append(_action(
                p, summary, "HISTORICAL_INVALID_SCORE",
                f"{summary.get('invalid_score_count')} invalid FTHG/FTAG rows",
                "inspect rows with non-numeric or negative FTHG/FTAG",
                "HIGH",
            ))
        if int(summary.get("invalid_result_count") or 0) > 0:
            actions.append(_action(
                p, summary, "HISTORICAL_INVALID_RESULT",
                f"{summary.get('invalid_result_count')} invalid FTR rows",
                "inspect FTR values; allowed values are H/D/A",
                "HIGH",
            ))
        if int(summary.get("date_parse_failure_count") or 0) > 0:
            actions.append(_action(
                p, summary, "HISTORICAL_DATE_PARSE_FAILURE",
                f"{summary.get('date_parse_failure_count')} Date parse failures",
                "normalize Date column format",
                "MEDIUM",
            ))
        if int(summary.get("team_name_blank_count") or 0) > 0:
            actions.append(_action(
                p, summary, "HISTORICAL_BLANK_TEAM",
                f"{summary.get('team_name_blank_count')} blank HomeTeam/AwayTeam rows",
                "inspect blank HomeTeam/AwayTeam rows",
                "HIGH",
            ))

    elif file_type == "FIXTURE_CSV":
        if int(summary.get("row_count") or 0) == 0:
            actions.append(_action(
                p, summary, "EMPTY_FIXTURE_FILE",
                "fixture file has zero rows",
                "refresh fixture file from trusted source or leave absent until fixtures exist",
                "LOW",
            ))
        elif str(summary.get("missing_contract_columns", "")).strip():
            actions.append(_action(
                p, summary, "MANUAL_REVIEW_REQUIRED",
                str(summary.get("missing_contract_columns", "")),
                "add date/home_team/away_team or Date/HomeTeam/AwayTeam",
                "MEDIUM",
            ))

    elif file_type == "ODDS_CSV" and str(summary.get("missing_contract_columns", "")).strip():
        actions.append(_action(
            p, summary, "ODDS_CONTRACT_MISSING_TRIPLET",
            str(summary.get("missing_contract_columns", "")),
            "add B365H/B365D/B365A or odds_home/odds_draw/odds_away",
            "MEDIUM",
        ))

    elif file_type == "XG_CSV" and str(summary.get("missing_contract_columns", "")).strip():
        actions.append(_action(
            p, summary, "XG_CONTRACT_MISSING_PAIR",
            str(summary.get("missing_contract_columns", "")),
            "add home_xg/away_xg or xG_home/xG_away or hxg/axg",
            "MEDIUM",
        ))

    elif file_type == "UNKNOWN_CSV":
        actions.append(_action(
            p, summary, "UNKNOWN_CSV_TYPE",
            "file does not match a known Phase 12.2 CSV contract",
            "classify manually or add importer adapter/contract mapping",
            "MEDIUM",
        ))

    elif file_type == "TEMPLATE_CSV":
        actions.append(_action(
            p, summary, "TEMPLATE_ONLY_NO_ACTION",
            "template file",
            "no repair required",
            "LOW",
        ))

    elif file_type == "PROCESSED_FEATURE_CSV":
        actions.append(_action(
            p, summary, "PROCESSED_FEATURE_NO_ACTION",
            "processed feature file",
            "no repair required unless used as replay source",
            "LOW",
        ))

    if not actions and label in {
        "READY_FOR_REPLAY",
        "READY_FOR_FIXTURES",
        "READY_FOR_ODDS_ENRICHMENT",
        "READY_FOR_XG_ENRICHMENT",
        "PROCESSED_FEATURE_READY",
        "TEMPLATE_ONLY",
    }:
        actions.append(_action(
            p, summary, "READY_NO_ACTION",
            "contract ready",
            "no repair required",
            "LOW",
        ))

    if not actions:
        actions.append(_action(
            p, summary, "MANUAL_REVIEW_REQUIRED",
            str(summary.get("missing_contract_columns", "")),
            "review file contract and decide whether an importer mapping is needed",
            "MEDIUM",
        ))
    return actions


def build_repair_plan_for_files(paths: Iterable[str | Path]) -> list[RepairAction]:
    actions: list[RepairAction] = []
    for path in paths:
        p = Path(path)
        try:
            df = pd.read_csv(p, low_memory=False)
        except Exception:
            df = pd.DataFrame()
        actions.extend(build_repair_plan_for_dataframe(p, df))
    return actions


def write_repair_preview(
    source_path: str | Path,
    df: pd.DataFrame,
    repair_action: RepairAction,
    output_dir: str | Path = "outputs/repair_preview",
) -> Path | None:
    """Write a safe preview copy only when the action explicitly supports it."""
    if not repair_action.auto_repair_supported:
        return None
    source = Path(source_path).resolve()
    preview = safe_preview_output_path(source, output_dir).resolve()
    if preview == source:
        raise ValueError("repair preview path must not equal source path")
    output_root = Path(output_dir).resolve()
    if output_root not in preview.parents and preview != output_root:
        raise ValueError("repair preview path must stay under output_dir")
    preview.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(preview, index=False)
    return preview
