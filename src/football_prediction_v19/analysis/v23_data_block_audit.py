# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


HARD_BLOCK_REASONS = {
    "fixture_missing",
    "fixture_ambiguous",
    "result_missing_for_backtest",
    "table_form_missing",
    "leakage_blocked",
    "unsupported_league",
    "corrupt_corpus_row",
    "no_core_source_available",
}

NON_HARD_MISSING_DATA = {
    "missing_xg",
    "missing_odds",
    "missing_lineups",
    "missing_injuries",
    "understat_failed_parse",
    "odds_match_not_found",
}


def classify_block_reason(row: dict[str, object] | pd.Series) -> dict[str, object]:
    data = dict(row)
    reason = str(data.get("block_reason_code", "") or "").strip()
    decision = str(data.get("decision_class", "") or "")
    if not reason and decision == "DATA_BLOCKED":
        if not _truthy(data.get("corpus_row_available", True)):
            reason = "fixture_missing"
        elif not _truthy(data.get("result_available", bool(data.get("actual_result", "")))):
            reason = "result_missing_for_backtest"
        elif str(data.get("leakage_status", "")).upper() == "BLOCKED":
            reason = "leakage_blocked"
        else:
            reason = "table_form_missing"
    if not reason and not _truthy(data.get("xg_available", False)):
        reason = "missing_xg"
    if not reason and not _truthy(data.get("odds_available", False)):
        reason = "missing_odds"
    is_hard = reason in HARD_BLOCK_REASONS
    should_non_block = reason in NON_HARD_MISSING_DATA
    return {
        "block_reason_code": reason,
        "block_reason_text": _reason_text(reason),
        "is_hard_block": is_hard,
        "should_have_been_non_blocking": should_non_block,
        "recommended_fix": _recommended_fix(reason, should_non_block),
    }


def build_data_block_audit(results: pd.DataFrame, output_dir: str | Path) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    blocked = results[results["decision_class"].astype(str).eq("DATA_BLOCKED")].copy() if not results.empty and "decision_class" in results.columns else pd.DataFrame()
    rows: list[dict[str, object]] = []
    for _, row in blocked.iterrows():
        classified = classify_block_reason(row)
        rows.append(
            {
                "canonical_match_id": row.get("match_id", row.get("canonical_match_id", "")),
                "competition": row.get("competition", ""),
                "season": row.get("season", ""),
                "match_date": row.get("match_date", ""),
                "home_team": row.get("home_team", ""),
                "away_team": row.get("away_team", ""),
                "corpus_row_available": True,
                "result_available": bool(str(row.get("actual_result", "")).strip()),
                "table_form_available": classified["block_reason_code"] != "table_form_missing",
                "xg_available": _truthy(row.get("xg_available", False)),
                "odds_available": _truthy(row.get("odds_available", False)),
                "fixture_status": "RESOLVED" if row.get("home_team") and row.get("away_team") else "NOT_FOUND",
                "eligibility_class_before_block": row.get("eligibility_class", ""),
                "block_stage": _block_stage(str(classified["block_reason_code"])),
                **classified,
            }
        )
    audit = pd.DataFrame(rows, columns=_AUDIT_COLUMNS)
    csv_path = out / "data_block_audit.csv"
    json_path = out / "data_block_audit.json"
    report_path = out / "data_block_audit_report.md"
    audit.to_csv(csv_path, index=False)
    json_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    report_path.write_text(
        "# v2.3 DATA_BLOCKED Audit\n\n"
        + f"- blocked_rows: {len(audit)}\n"
        + f"- hard_blocks: {int(audit['is_hard_block'].sum()) if not audit.empty else 0}\n"
        + f"- invalid_non_hard_blocks: {int(audit['should_have_been_non_blocking'].sum()) if not audit.empty else 0}\n",
        encoding="utf-8",
    )
    return {
        "v23_data_block_audit_status": "READY",
        "data_block_audit_csv_path": str(csv_path.resolve()),
        "data_block_audit_json_path": str(json_path.resolve()),
        "data_block_audit_report_path": str(report_path.resolve()),
        "blocked_rows": len(audit),
    }


def _block_stage(reason: str) -> str:
    if reason in {"fixture_missing", "fixture_ambiguous"}:
        return "RESOLVER"
    if reason in {"result_missing_for_backtest", "corrupt_corpus_row", "no_core_source_available"}:
        return "CORPUS"
    if reason == "leakage_blocked":
        return "ASOF_FEATURES"
    if reason in {"table_form_missing", "unsupported_league"}:
        return "ELIGIBILITY"
    if reason in NON_HARD_MISSING_DATA:
        return "DECISION_POLICY"
    return "FEATURE_STORE"


def _reason_text(reason: str) -> str:
    return {
        "fixture_missing": "Fixture could not be resolved.",
        "fixture_ambiguous": "Fixture resolution was ambiguous.",
        "result_missing_for_backtest": "Backtest row has no known result.",
        "table_form_missing": "Core table/form source is missing.",
        "leakage_blocked": "As-of leakage guard blocked the row.",
        "unsupported_league": "League is unsupported by the winner core.",
        "corrupt_corpus_row": "Required corpus identity fields are blank or corrupt.",
        "no_core_source_available": "No football-data style core source is available.",
        "missing_xg": "xG is missing; this should cap confidence, not hard block.",
        "missing_odds": "Odds are missing; this should be a risk note, not a hard block.",
    }.get(reason, "Unclassified block reason.")


def _recommended_fix(reason: str, should_non_block: bool) -> str:
    if should_non_block:
        return "Route missing optional data to risk notes and partial model confidence caps."
    if reason in HARD_BLOCK_REASONS:
        return "Keep hard block unless source data can be repaired."
    return "Classify the block reason and verify it is not optional missing data."


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


_AUDIT_COLUMNS = [
    "canonical_match_id",
    "competition",
    "season",
    "match_date",
    "home_team",
    "away_team",
    "corpus_row_available",
    "result_available",
    "table_form_available",
    "xg_available",
    "odds_available",
    "fixture_status",
    "eligibility_class_before_block",
    "block_stage",
    "block_reason_code",
    "block_reason_text",
    "is_hard_block",
    "should_have_been_non_blocking",
    "recommended_fix",
]
