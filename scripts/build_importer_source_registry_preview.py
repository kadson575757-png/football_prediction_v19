# -*- coding: utf-8 -*-
"""Build a preview registry for planned external importer sources.

No network calls are made. This is a contract/registry preview only.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

IMPORTER_SOURCE_REGISTRY_PREVIEW_READY = "IMPORTER_SOURCE_REGISTRY_PREVIEW_READY"
IMPORTER_SOURCE_REGISTERED = "IMPORTER_SOURCE_REGISTERED"
IMPORTER_SOURCE_CONTRACT_PENDING = "IMPORTER_SOURCE_CONTRACT_PENDING"
IMPORTER_SOURCE_NETWORK_DISABLED_BY_DESIGN = "IMPORTER_SOURCE_NETWORK_DISABLED_BY_DESIGN"
IMPORTER_SOURCE_REGISTRY_PREVIEW_BLOCKED_UNSAFE_PATH = "IMPORTER_SOURCE_REGISTRY_PREVIEW_BLOCKED_UNSAFE_PATH"

OUTPUT_DIR = ROOT / "outputs" / "importer_preview"
OUTPUT_CSV = "importer_source_registry_preview.csv"
OUTPUT_MD = "importer_source_registry_preview.md"

REGISTRY_COLUMNS = [
    "source_id",
    "provider_name",
    "source_type",
    "access_mode",
    "network_required",
    "network_calls_enabled",
    "supports_historical_matches",
    "supports_upcoming_fixtures",
    "supports_team_stats",
    "supports_player_stats",
    "supports_xg",
    "supports_xa",
    "supports_lineups",
    "supports_odds",
    "canonical_match_schema_status",
    "canonical_team_schema_status",
    "canonical_player_schema_status",
    "implementation_status",
    "recommendation",
    "notes",
]


SOURCE_ROWS: list[dict[str, Any]] = [
    {
        "source_id": "fbref",
        "provider_name": "FBref",
        "source_type": "website_export",
        "access_mode": "manual_export_or_future_adapter",
        "network_required": True,
        "network_calls_enabled": False,
        "supports_historical_matches": True,
        "supports_upcoming_fixtures": False,
        "supports_team_stats": True,
        "supports_player_stats": True,
        "supports_xg": True,
        "supports_xa": True,
        "supports_lineups": False,
        "supports_odds": False,
        "canonical_match_schema_status": IMPORTER_SOURCE_CONTRACT_PENDING,
        "canonical_team_schema_status": IMPORTER_SOURCE_CONTRACT_PENDING,
        "canonical_player_schema_status": IMPORTER_SOURCE_CONTRACT_PENDING,
        "implementation_status": IMPORTER_SOURCE_NETWORK_DISABLED_BY_DESIGN,
        "recommendation": IMPORTER_SOURCE_REGISTERED,
        "notes": "Preview contract only; no FBref scraping is active.",
    },
    {
        "source_id": "understat",
        "provider_name": "Understat",
        "source_type": "website_export_or_optional_provider",
        "access_mode": "manual_export_or_future_adapter",
        "network_required": True,
        "network_calls_enabled": False,
        "supports_historical_matches": True,
        "supports_upcoming_fixtures": False,
        "supports_team_stats": True,
        "supports_player_stats": True,
        "supports_xg": True,
        "supports_xa": True,
        "supports_lineups": False,
        "supports_odds": False,
        "canonical_match_schema_status": IMPORTER_SOURCE_CONTRACT_PENDING,
        "canonical_team_schema_status": IMPORTER_SOURCE_CONTRACT_PENDING,
        "canonical_player_schema_status": IMPORTER_SOURCE_CONTRACT_PENDING,
        "implementation_status": IMPORTER_SOURCE_NETWORK_DISABLED_BY_DESIGN,
        "recommendation": IMPORTER_SOURCE_REGISTERED,
        "notes": "Existing trusted-source workflow remains local/export-based unless explicitly enabled in future phases.",
    },
    {
        "source_id": "fotmob",
        "provider_name": "FotMob",
        "source_type": "api_or_website",
        "access_mode": "future_adapter_only",
        "network_required": True,
        "network_calls_enabled": False,
        "supports_historical_matches": True,
        "supports_upcoming_fixtures": True,
        "supports_team_stats": True,
        "supports_player_stats": True,
        "supports_xg": True,
        "supports_xa": True,
        "supports_lineups": True,
        "supports_odds": False,
        "canonical_match_schema_status": IMPORTER_SOURCE_CONTRACT_PENDING,
        "canonical_team_schema_status": IMPORTER_SOURCE_CONTRACT_PENDING,
        "canonical_player_schema_status": IMPORTER_SOURCE_CONTRACT_PENDING,
        "implementation_status": IMPORTER_SOURCE_NETWORK_DISABLED_BY_DESIGN,
        "recommendation": IMPORTER_SOURCE_REGISTERED,
        "notes": "Future adapter candidate; no live access in this phase.",
    },
    {
        "source_id": "sofascore",
        "provider_name": "SofaScore",
        "source_type": "api_or_website",
        "access_mode": "future_adapter_only",
        "network_required": True,
        "network_calls_enabled": False,
        "supports_historical_matches": True,
        "supports_upcoming_fixtures": True,
        "supports_team_stats": True,
        "supports_player_stats": True,
        "supports_xg": True,
        "supports_xa": False,
        "supports_lineups": True,
        "supports_odds": False,
        "canonical_match_schema_status": IMPORTER_SOURCE_CONTRACT_PENDING,
        "canonical_team_schema_status": IMPORTER_SOURCE_CONTRACT_PENDING,
        "canonical_player_schema_status": IMPORTER_SOURCE_CONTRACT_PENDING,
        "implementation_status": IMPORTER_SOURCE_NETWORK_DISABLED_BY_DESIGN,
        "recommendation": IMPORTER_SOURCE_REGISTERED,
        "notes": "Future adapter candidate; no live access in this phase.",
    },
    {
        "source_id": "whoscored",
        "provider_name": "WhoScored",
        "source_type": "website",
        "access_mode": "future_adapter_only",
        "network_required": True,
        "network_calls_enabled": False,
        "supports_historical_matches": True,
        "supports_upcoming_fixtures": False,
        "supports_team_stats": True,
        "supports_player_stats": True,
        "supports_xg": False,
        "supports_xa": False,
        "supports_lineups": True,
        "supports_odds": False,
        "canonical_match_schema_status": IMPORTER_SOURCE_CONTRACT_PENDING,
        "canonical_team_schema_status": IMPORTER_SOURCE_CONTRACT_PENDING,
        "canonical_player_schema_status": IMPORTER_SOURCE_CONTRACT_PENDING,
        "implementation_status": IMPORTER_SOURCE_NETWORK_DISABLED_BY_DESIGN,
        "recommendation": IMPORTER_SOURCE_REGISTERED,
        "notes": "Future adapter candidate; no live scraping in this phase.",
    },
    {
        "source_id": "soccerdata",
        "provider_name": "soccerdata",
        "source_type": "python_library",
        "access_mode": "optional_future_provider",
        "network_required": True,
        "network_calls_enabled": False,
        "supports_historical_matches": True,
        "supports_upcoming_fixtures": False,
        "supports_team_stats": True,
        "supports_player_stats": True,
        "supports_xg": True,
        "supports_xa": True,
        "supports_lineups": False,
        "supports_odds": False,
        "canonical_match_schema_status": IMPORTER_SOURCE_CONTRACT_PENDING,
        "canonical_team_schema_status": IMPORTER_SOURCE_CONTRACT_PENDING,
        "canonical_player_schema_status": IMPORTER_SOURCE_CONTRACT_PENDING,
        "implementation_status": IMPORTER_SOURCE_NETWORK_DISABLED_BY_DESIGN,
        "recommendation": IMPORTER_SOURCE_REGISTERED,
        "notes": "Optional provider remains disabled until a later explicit phase.",
    },
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--write-preview", action="store_true")
    parser.add_argument("--sources", default=None, help="Comma-separated source IDs. Defaults to all supported preview sources.")
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _safe_output_dir(output_dir: str | Path, base_dir: Path) -> Path:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base_dir / out
    resolved = out.resolve()
    allowed = (base_dir / "outputs" / "importer_preview").resolve()
    if resolved != allowed and allowed not in resolved.parents:
        raise ValueError("IMPORTER_PREVIEW_OUTPUT_DIR_MUST_BE_UNDER_OUTPUTS_IMPORTER_PREVIEW")
    return resolved


def build_registry_frame(sources: str | None = None) -> pd.DataFrame:
    selected = None
    if sources:
        selected = {item.strip().lower() for item in sources.split(",") if item.strip()}
    rows = [row for row in SOURCE_ROWS if selected is None or row["source_id"] in selected]
    return pd.DataFrame(rows, columns=REGISTRY_COLUMNS)


def build_markdown(table: pd.DataFrame) -> str:
    lines = [
        "# Phase 15.1 Importer Source Registry Preview",
        "",
        "Phase 15.1 is a registry/adapter contract preview only.",
        "",
        "## A. Executive Summary",
        f"- sources registered: {len(table)}",
        "- network calls enabled: false",
        "- live scraping active: false",
        "",
        "## B. Source Registry",
        "| source_id | provider_name | implementation_status | supports_xg | supports_odds |",
        "| --- | --- | --- | --- | --- |",
    ]
    for _, row in table.iterrows():
        lines.append(f"| {row['source_id']} | {row['provider_name']} | {row['implementation_status']} | {row['supports_xg']} | {row['supports_odds']} |")
    lines += [
        "",
        "## C. Safety Notes",
        "- No network calls are made.",
        "- No live scraping is active.",
        "- Future phases should implement one source adapter at a time.",
        "- Importer work is separate from xG model integration.",
        "- No model, probability, market, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "",
        "## D. Recommendation",
        IMPORTER_SOURCE_REGISTRY_PREVIEW_READY,
        "",
    ]
    return "\n".join(lines)


def _blocked(status: str, reason: str) -> dict[str, Any]:
    return {
        "importer_registry_status": status,
        "sources_registered": 0,
        "network_calls_enabled": False,
        "registry_output_path": "",
        "registry_summary_path": "",
        "recommendation": status,
        "blocking_reasons": reason,
    }


def build_importer_source_registry_preview(
    *,
    output_dir: str | Path = OUTPUT_DIR,
    write_preview: bool = False,
    sources: str | None = None,
    base_dir: str | Path = ROOT,
) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    try:
        out_dir = _safe_output_dir(output_dir, base)
    except ValueError as exc:
        return _blocked(IMPORTER_SOURCE_REGISTRY_PREVIEW_BLOCKED_UNSAFE_PATH, str(exc))
    table = build_registry_frame(sources)
    csv_path = ""
    md_path = ""
    if write_preview:
        out_dir.mkdir(parents=True, exist_ok=True)
        csv_file = (out_dir / OUTPUT_CSV).resolve()
        md_file = (out_dir / OUTPUT_MD).resolve()
        if out_dir not in csv_file.parents or out_dir not in md_file.parents:
            return _blocked(IMPORTER_SOURCE_REGISTRY_PREVIEW_BLOCKED_UNSAFE_PATH, "REGISTRY_OUTPUT_OUTSIDE_OUTPUT_DIR")
        table.to_csv(csv_file, index=False)
        md_file.write_text(build_markdown(table), encoding="utf-8")
        csv_path = str(csv_file)
        md_path = str(md_file)
    return {
        "importer_registry_status": IMPORTER_SOURCE_REGISTRY_PREVIEW_READY,
        "sources_registered": int(len(table)),
        "network_calls_enabled": False,
        "registry_output_path": csv_path,
        "registry_summary_path": md_path,
        "recommendation": IMPORTER_SOURCE_REGISTRY_PREVIEW_READY,
        "blocking_reasons": "",
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_importer_source_registry_preview(
        output_dir=args.output_dir,
        write_preview=args.write_preview,
        sources=args.sources,
        base_dir=args.base_dir,
    )
    for key in [
        "importer_registry_status",
        "sources_registered",
        "network_calls_enabled",
        "registry_output_path",
        "registry_summary_path",
        "recommendation",
    ]:
        print(f"{key}={str(summary[key]).lower() if key == 'network_calls_enabled' else summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
