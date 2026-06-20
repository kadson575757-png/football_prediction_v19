# -*- coding: utf-8 -*-
"""Build canonical importer schema contract previews.

No network calls are made. This is a schema/adapter contract preview only.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_importer_source_registry_preview import build_importer_source_registry_preview  # noqa: E402

IMPORTER_SCHEMA_CONTRACTS_PREVIEW_READY = "IMPORTER_SCHEMA_CONTRACTS_PREVIEW_READY"
IMPORTER_SCHEMA_CONTRACT_REGISTERED = "IMPORTER_SCHEMA_CONTRACT_REGISTERED"
IMPORTER_SCHEMA_CONTRACT_PENDING_ADAPTER = "IMPORTER_SCHEMA_CONTRACT_PENDING_ADAPTER"
IMPORTER_SCHEMA_NETWORK_DISABLED_BY_DESIGN = "IMPORTER_SCHEMA_NETWORK_DISABLED_BY_DESIGN"
IMPORTER_SCHEMA_CONTRACTS_PREVIEW_BLOCKED_UNSAFE_PATH = "IMPORTER_SCHEMA_CONTRACTS_PREVIEW_BLOCKED_UNSAFE_PATH"

OUTPUT_DIR = ROOT / "outputs" / "importer_preview"
OUTPUT_CSV = "importer_schema_contracts_preview.csv"
OUTPUT_MD = "importer_schema_contracts_preview.md"

CONTRACT_COLUMNS = [
    "contract_id",
    "entity_type",
    "field_name",
    "field_type",
    "required",
    "nullable",
    "canonical_description",
    "example_value",
    "supported_sources",
    "validation_rule",
    "implementation_status",
    "recommendation",
    "notes",
    "network_calls_enabled",
]

SUPPORTED_ALL = "fbref | understat | fotmob | sofascore | whoscored | soccerdata"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default=str(OUTPUT_DIR / "importer_source_registry_preview.csv"))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--write-preview", action="store_true")
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _safe_output_dir(output_dir: str | Path, base_dir: Path) -> Path:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base_dir / out
    resolved = out.resolve()
    allowed = (base_dir / "outputs" / "importer_preview").resolve()
    if resolved != allowed and allowed not in resolved.parents:
        raise ValueError("IMPORTER_SCHEMA_OUTPUT_DIR_MUST_BE_UNDER_OUTPUTS_IMPORTER_PREVIEW")
    return resolved


def _field(contract_id: str, field_name: str, field_type: str, required: bool, nullable: bool, description: str, example: str, sources: str, rule: str, notes: str = "") -> dict[str, Any]:
    return {
        "contract_id": contract_id,
        "entity_type": contract_id,
        "field_name": field_name,
        "field_type": field_type,
        "required": required,
        "nullable": nullable,
        "canonical_description": description,
        "example_value": example,
        "supported_sources": sources,
        "validation_rule": rule,
        "implementation_status": IMPORTER_SCHEMA_NETWORK_DISABLED_BY_DESIGN,
        "recommendation": IMPORTER_SCHEMA_CONTRACT_REGISTERED,
        "notes": notes or "Contract preview only; adapter pending.",
        "network_calls_enabled": False,
    }


def build_contract_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, typ, req, nullable, example, rule in [
        ("source_id", "string", True, False, "fbref", "non_empty_string"),
        ("provider_match_id", "string", True, False, "123456", "non_empty_string"),
        ("league", "string", True, False, "Bundesliga", "non_empty_string"),
        ("season", "string", True, False, "2024", "non_empty_string"),
        ("date", "date", True, False, "2024-08-23", "parseable_date"),
        ("home_team", "string", True, False, "Bayern Munich", "non_empty_string"),
        ("away_team", "string", True, False, "Leverkusen", "non_empty_string"),
        ("home_goals", "integer", False, True, "2", "integer_or_null"),
        ("away_goals", "integer", False, True, "1", "integer_or_null"),
        ("match_status", "string", True, False, "finished", "scheduled_or_live_or_finished"),
    ]:
        rows.append(_field("canonical_match", name, typ, req, nullable, f"Canonical match field {name}.", example, SUPPORTED_ALL, rule))
    for cid, fields in {
        "canonical_team_match_stats": ["source_id", "provider_match_id", "team", "opponent", "shots", "possession_pct", "xg"],
        "canonical_player_match_stats": ["source_id", "provider_match_id", "player", "team", "minutes", "shots", "xg", "xa"],
        "canonical_fixture": ["source_id", "provider_match_id", "league", "season", "date", "home_team", "away_team", "fixture_status"],
        "canonical_lineup": ["source_id", "provider_match_id", "team", "player", "position", "is_starter"],
    }.items():
        for name in fields:
            rows.append(_field(cid, name, "string", name in {"source_id", "provider_match_id"}, name not in {"source_id", "provider_match_id"}, f"Canonical {cid} field {name}.", name, SUPPORTED_ALL, "contract_only"))
    for name, typ, req, nullable, example, rule in [
        ("source_id", "string", True, False, "understat", "non_empty_string"),
        ("provider_match_id", "string", True, False, "123456", "non_empty_string"),
        ("market_type", "string", True, False, "1x2", "non_empty_string"),
        ("bookmaker", "string", True, False, "B365", "non_empty_string"),
        ("odds_home", "float", False, True, "2.10", "positive_number_or_null"),
        ("odds_draw", "float", False, True, "3.40", "positive_number_or_null"),
        ("odds_away", "float", False, True, "3.20", "positive_number_or_null"),
        ("captured_at", "datetime", True, False, "2024-08-23T12:00:00Z", "parseable_datetime"),
    ]:
        rows.append(_field("canonical_odds_snapshot", name, typ, req, nullable, f"Canonical odds snapshot field {name}.", example, "future_odds_adapter", rule, "Contract-only; no odds fetching is implemented."))
    for name, typ, req, nullable, example, rule in [
        ("source_id", "string", True, False, "understat", "non_empty_string"),
        ("provider_match_id", "string", True, False, "123456", "non_empty_string"),
        ("home_team", "string", True, False, "Bayern Munich", "non_empty_string"),
        ("away_team", "string", True, False, "Leverkusen", "non_empty_string"),
        ("date", "date", True, False, "2024-08-23", "parseable_date"),
        ("home_xg", "float", True, False, "1.8", "non_negative_number"),
        ("away_xg", "float", True, False, "0.9", "non_negative_number"),
        ("xg_provider", "string", True, False, "Understat", "non_empty_string"),
        ("xg_access_label", "string", True, False, "manual_export", "non_empty_string"),
    ]:
        rows.append(_field("canonical_xg_source", name, typ, req, nullable, f"Canonical xG source field {name}.", example, "fbref | understat | fotmob | soccerdata", rule))
    return rows


def build_contracts_frame() -> pd.DataFrame:
    return pd.DataFrame(build_contract_rows(), columns=CONTRACT_COLUMNS)


def build_markdown(table: pd.DataFrame) -> str:
    contracts = sorted(table["contract_id"].unique())
    lines = [
        "# Phase 15.2 Canonical Importer Schema Contracts Preview",
        "",
        "Phase 15.2 defines schema contracts only. No live scraping or API fetching is active.",
        "",
        "## A. Executive Summary",
        f"- contracts registered: {len(contracts)}",
        f"- fields registered: {len(table)}",
        "- network calls enabled: false",
        "",
        "## B. Contracts",
        "| contract_id | fields |",
        "| --- | --- |",
    ]
    for contract in contracts:
        lines.append(f"| {contract} | {int(table['contract_id'].eq(contract).sum())} |")
    lines += [
        "",
        "## C. Safety Notes",
        "- Future phases should implement one adapter at a time against these contracts.",
        "- Imported data cannot influence model logic until a separate explicit integration phase.",
        "- No model, probability, market, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "",
        "## D. Recommendation",
        IMPORTER_SCHEMA_CONTRACTS_PREVIEW_READY,
        "",
    ]
    return "\n".join(lines)


def _blocked(status: str, reason: str) -> dict[str, Any]:
    return {
        "importer_schema_contracts_status": status,
        "contracts_registered": 0,
        "fields_registered": 0,
        "network_calls_enabled": False,
        "contracts_output_path": "",
        "contracts_summary_path": "",
        "recommendation": status,
        "blocking_reasons": reason,
    }


def build_importer_schema_contracts_preview(
    *,
    registry: str | Path = OUTPUT_DIR / "importer_source_registry_preview.csv",
    output_dir: str | Path = OUTPUT_DIR,
    write_preview: bool = False,
    base_dir: str | Path = ROOT,
) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    try:
        out_dir = _safe_output_dir(output_dir, base)
    except ValueError as exc:
        return _blocked(IMPORTER_SCHEMA_CONTRACTS_PREVIEW_BLOCKED_UNSAFE_PATH, str(exc))
    registry_path = Path(registry)
    if not registry_path.is_absolute():
        registry_path = base / registry_path
    if not registry_path.exists():
        build_importer_source_registry_preview(output_dir=out_dir, write_preview=True, base_dir=base)
    table = build_contracts_frame()
    csv_path = ""
    md_path = ""
    if write_preview:
        out_dir.mkdir(parents=True, exist_ok=True)
        csv_file = (out_dir / OUTPUT_CSV).resolve()
        md_file = (out_dir / OUTPUT_MD).resolve()
        if out_dir not in csv_file.parents or out_dir not in md_file.parents:
            return _blocked(IMPORTER_SCHEMA_CONTRACTS_PREVIEW_BLOCKED_UNSAFE_PATH, "CONTRACT_OUTPUT_OUTSIDE_OUTPUT_DIR")
        table.to_csv(csv_file, index=False)
        md_file.write_text(build_markdown(table), encoding="utf-8")
        csv_path = str(csv_file)
        md_path = str(md_file)
    return {
        "importer_schema_contracts_status": IMPORTER_SCHEMA_CONTRACTS_PREVIEW_READY,
        "contracts_registered": int(table["contract_id"].nunique()),
        "fields_registered": int(len(table)),
        "network_calls_enabled": False,
        "contracts_output_path": csv_path,
        "contracts_summary_path": md_path,
        "recommendation": IMPORTER_SCHEMA_CONTRACTS_PREVIEW_READY,
        "blocking_reasons": "",
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_importer_schema_contracts_preview(registry=args.registry, output_dir=args.output_dir, write_preview=args.write_preview, base_dir=args.base_dir)
    for key in ["importer_schema_contracts_status", "contracts_registered", "fields_registered", "network_calls_enabled", "contracts_output_path", "contracts_summary_path", "recommendation"]:
        print(f"{key}={str(summary[key]).lower() if key == 'network_calls_enabled' else summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
