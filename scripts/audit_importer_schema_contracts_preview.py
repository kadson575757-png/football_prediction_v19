# -*- coding: utf-8 -*-
"""Audit Phase 15.2 importer schema contracts preview."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

IMPORTER_SCHEMA_CONTRACTS_PREVIEW_READY = "IMPORTER_SCHEMA_CONTRACTS_PREVIEW_READY"
BUILD_IMPORTER_SCHEMA_CONTRACTS_PREVIEW = "BUILD_IMPORTER_SCHEMA_CONTRACTS_PREVIEW"
FIX_IMPORTER_SCHEMA_CONTRACTS_PREVIEW = "FIX_IMPORTER_SCHEMA_CONTRACTS_PREVIEW"

OUTPUT_CSV = "importer_schema_contracts_preview_summary.csv"
OUTPUT_MD = "importer_schema_contracts_preview_summary.md"

EXPECTED_CONTRACT_IDS = [
    "canonical_match",
    "canonical_team_match_stats",
    "canonical_player_match_stats",
    "canonical_fixture",
    "canonical_lineup",
    "canonical_odds_snapshot",
    "canonical_xg_source",
]
REQUIRED_COLUMNS = {
    "contract_id", "entity_type", "field_name", "field_type", "required", "nullable",
    "canonical_description", "example_value", "supported_sources", "validation_rule",
    "implementation_status", "recommendation", "notes", "network_calls_enabled",
}
REQUIRED_MATCH_FIELDS = {"source_id", "provider_match_id", "league", "season", "date", "home_team", "away_team", "home_goals", "away_goals", "match_status"}
REQUIRED_XG_FIELDS = {"source_id", "provider_match_id", "home_team", "away_team", "date", "home_xg", "away_xg", "xg_provider", "xg_access_label"}
PREVIEW_ONLY_STATUSES = {"IMPORTER_SCHEMA_NETWORK_DISABLED_BY_DESIGN", "IMPORTER_SCHEMA_CONTRACT_PENDING_ADAPTER", "IMPORTER_SCHEMA_CONTRACT_REGISTERED"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contracts", default=None)
    parser.add_argument("--preview-dir", default=str(ROOT / "outputs" / "importer_preview"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _contracts_path(contracts: str | Path | None, preview_dir: str | Path) -> Path | None:
    if contracts:
        return Path(contracts)
    path = Path(preview_dir) / "importer_schema_contracts_preview.csv"
    return path if path.exists() else None


def _under_preview(path_text: str, base: Path) -> bool:
    path = Path(path_text)
    if not path.is_absolute():
        path = base / path
    try:
        resolved = path.resolve()
    except OSError:
        return False
    allowed = (base / "outputs" / "importer_preview").resolve()
    return resolved == allowed or allowed in resolved.parents


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def audit_contracts(path: Path, *, base_dir: str | Path = ROOT) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    errors: list[str] = []
    if not _under_preview(str(path), base):
        errors.append("UNSAFE_CONTRACTS_PATH")
    try:
        table = pd.read_csv(path, low_memory=False)
    except Exception as exc:
        return {
            "contracts_path": str(path),
            "contracts_found": 0,
            "fields_found": 0,
            "missing_contract_ids": "ALL",
            "missing_required_columns": "ALL",
            "missing_canonical_match_fields": "ALL",
            "missing_canonical_xg_source_fields": "ALL",
            "network_calls_enabled": True,
            "preview_only_statuses": False,
            "contracts_valid": False,
            "blocking_reasons": " | ".join([*errors, str(exc)]),
        }
    missing_cols = sorted(REQUIRED_COLUMNS - set(table.columns))
    if missing_cols:
        errors.append("MISSING_REQUIRED_COLUMNS")
    contract_ids = set(table["contract_id"].astype(str)) if "contract_id" in table.columns else set()
    missing_contracts = [cid for cid in EXPECTED_CONTRACT_IDS if cid not in contract_ids]
    if missing_contracts:
        errors.append("MISSING_EXPECTED_CONTRACT_IDS")
    def fields_for(contract_id: str) -> set[str]:
        if not {"contract_id", "field_name"}.issubset(table.columns):
            return set()
        return set(table.loc[table["contract_id"].astype(str).eq(contract_id), "field_name"].astype(str))
    missing_match = sorted(REQUIRED_MATCH_FIELDS - fields_for("canonical_match"))
    if missing_match:
        errors.append("MISSING_CANONICAL_MATCH_FIELDS")
    missing_xg = sorted(REQUIRED_XG_FIELDS - fields_for("canonical_xg_source"))
    if missing_xg:
        errors.append("MISSING_CANONICAL_XG_SOURCE_FIELDS")
    network_enabled = any(_as_bool(value) for value in table["network_calls_enabled"]) if "network_calls_enabled" in table.columns else True
    if network_enabled:
        errors.append("NETWORK_CALLS_ENABLED")
    statuses = set(table["implementation_status"].astype(str)) if "implementation_status" in table.columns else set()
    preview_only = bool(statuses) and statuses.issubset(PREVIEW_ONLY_STATUSES)
    if not preview_only:
        errors.append("NON_PREVIEW_IMPLEMENTATION_STATUS")
    return {
        "contracts_path": str(path),
        "contracts_found": int(len(contract_ids)),
        "fields_found": int(len(table)),
        "missing_contract_ids": " | ".join(missing_contracts),
        "missing_required_columns": " | ".join(missing_cols),
        "missing_canonical_match_fields": " | ".join(missing_match),
        "missing_canonical_xg_source_fields": " | ".join(missing_xg),
        "network_calls_enabled": network_enabled,
        "preview_only_statuses": preview_only,
        "contracts_valid": not errors,
        "blocking_reasons": " | ".join(errors),
    }


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return BUILD_IMPORTER_SCHEMA_CONTRACTS_PREVIEW
    if table["contracts_valid"].any():
        return IMPORTER_SCHEMA_CONTRACTS_PREVIEW_READY
    return FIX_IMPORTER_SCHEMA_CONTRACTS_PREVIEW


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    lines = [
        "# Phase 15.2 Importer Schema Contracts Preview Audit",
        "",
        "Phase 15.2 is a schema/contract preview only. No network calls are made.",
        "",
        "## A. Executive Summary",
        f"- previews audited: {len(table)}",
        f"- valid previews: {int(table['contracts_valid'].sum()) if not table.empty else 0}",
        "",
        "## B. Diagnostics",
    ]
    if table.empty:
        lines += ["No importer schema contracts preview found.", ""]
    else:
        cols = ["contracts_found", "fields_found", "missing_contract_ids", "network_calls_enabled", "preview_only_statuses", "contracts_valid", "blocking_reasons"]
        lines += ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
        for _, row in table[cols].iterrows():
            lines.append("| " + " | ".join(str(row[col]).replace("|", ";") for col in cols) + " |")
        lines.append("")
    lines += [
        "## C. Safety Checks",
        "- No live scraping/API fetching is active.",
        "- No provider data is imported.",
        "- Imported data cannot influence model logic until a separate explicit integration phase.",
        "- No model, probability, market, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "",
        "## D. Phase 15.2 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(
    *,
    contracts: str | Path | None = None,
    preview_dir: str | Path = ROOT / "outputs" / "importer_preview",
    output_dir: str | Path = ROOT / "outputs" / "diagnostics",
    base_dir: str | Path = ROOT,
) -> tuple[pd.DataFrame, str, str]:
    path = _contracts_path(contracts, preview_dir)
    rows = [audit_contracts(path, base_dir=base_dir)] if path else []
    table = pd.DataFrame(rows)
    rec = recommendation(table)
    markdown = build_markdown(table, rec)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    table.to_csv(out / OUTPUT_CSV, index=False)
    (out / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown, rec


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, _markdown, rec = run(contracts=args.contracts, preview_dir=args.preview_dir, output_dir=args.output_dir, base_dir=args.base_dir)
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
