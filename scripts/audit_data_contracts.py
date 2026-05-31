# -*- coding: utf-8 -*-
"""Phase 12 data contract and importer readiness audit.

Diagnostic/foundation only. No scraping, credentials, network calls, model
probability changes, recommended-market changes, market-tier changes, betting,
staking, or ROI logic.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.data_contracts import summarize_data_quality_by_file_type  # noqa: E402
from football_prediction_v19.importers.registry import list_importers  # noqa: E402

OUTPUT_CSV = "data_contract_audit_summary.csv"
OUTPUT_MD = "data_contract_audit_summary.md"


def discover_csv_files(root: Path) -> list[Path]:
    patterns = (
        root / "data" / "raw" / "*.csv",
        root / "data" / "processed" / "*.csv",
        root / "data" / "*.csv",
    )
    paths: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for path in sorted(pattern.parent.glob(pattern.name)):
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                paths.append(path)
    return paths


def _infer_from_path(path: Path) -> tuple[str, str]:
    stem = path.stem
    parts = stem.split("_")
    season = next((part for part in parts if part.isdigit() and len(part) == 4), "")
    league = ""
    if len(parts) >= 3 and parts[0] == "football" and parts[1] == "data":
        league = parts[2]
    return league, season


def _safe_read_csv(path: Path) -> tuple[pd.DataFrame | None, str]:
    try:
        return pd.read_csv(path, low_memory=False), ""
    except Exception as exc:  # pragma: no cover - defensive IO guard
        return None, str(exc)


def audit_file(path: Path) -> dict[str, Any]:
    league, season = _infer_from_path(path)
    df, error = _safe_read_csv(path)
    if df is None:
        return {
            "file_path": str(path),
            "file_name": path.name,
            "league": league,
            "season": season,
            "load_error": error,
            "row_count": 0,
            "quality_label": "INVALID_DATA",
        }
    summary = summarize_data_quality_by_file_type(path, df, league=league, season=season)
    return {
        "file_path": str(path),
        "file_name": path.name,
        "load_error": "",
        **summary,
    }


def build_audit_table(root: Path) -> pd.DataFrame:
    rows = [audit_file(path) for path in discover_csv_files(root)]
    return pd.DataFrame(rows)


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return "INCONCLUSIVE_NO_DATA_FILES"
    historical = table[table["file_type"] == "HISTORICAL_MATCH_CSV"]
    historical_ready = table[table["replay_ready"] == True]
    fixture_like = table[table["file_type"] == "FIXTURE_CSV"]
    fixture_ready = table[table["fixture_ready"] == True]
    odds_xg = table[table["file_type"].isin(["ODDS_CSV", "XG_CSV"])]
    broken_historical = historical[
        historical["contract_quality_label"].isin(["MISSING_REQUIRED_COLUMNS", "INVALID_DATA", "EMPTY_DATA"])
    ]
    broken_fixtures = fixture_like[
        fixture_like["contract_quality_label"].isin(["MISSING_REQUIRED_COLUMNS", "INVALID_DATA", "EMPTY_DATA"])
    ]
    broken_odds_xg = odds_xg[
        odds_xg["contract_quality_label"].isin(["MISSING_REQUIRED_COLUMNS", "INVALID_DATA", "EMPTY_DATA"])
    ]
    if historical_ready.empty:
        return "ADD_HISTORICAL_DATA_FILES"
    if len(broken_historical) >= max(1, len(historical) // 2):
        return "FIX_HISTORICAL_MATCH_CONTRACTS_FIRST"
    if not fixture_like.empty and not broken_fixtures.empty:
        return "FIX_FIXTURE_CONTRACTS_FIRST"
    if not broken_odds_xg.empty:
        return "FIX_ODDS_OR_XG_CONTRACTS_FIRST"
    active_csv_importers = [
        item for item in list_importers()
        if item["source_type"] == "csv" and item["status"] == "ACTIVE"
    ]
    if not historical_ready.empty and (not fixture_like.empty or not fixture_ready.empty) and active_csv_importers:
        return "READY_FOR_IMPORTER_IMPLEMENTATION"
    return "READY_FOR_IMPORTER_IMPLEMENTATION"


def _section_table(df: pd.DataFrame, columns: list[str]) -> list[str]:
    if df.empty:
        return ["No rows.", ""]
    cols = [col for col in columns if col in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in df[cols].iterrows():
        values = [str(row.get(col, "")) for col in cols]
        lines.append("| " + " | ".join(values) + " |")
    lines.append("")
    return lines


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    total = int(len(table))
    replay = table[table["replay_ready"] == True] if not table.empty else pd.DataFrame()
    fixtures = table[table["fixture_ready"] == True] if not table.empty else pd.DataFrame()
    odds = table[table["odds_ready"] == True] if not table.empty else pd.DataFrame()
    xg = table[table["xg_ready"] == True] if not table.empty else pd.DataFrame()
    templates = table[table["template_only"] == True] if not table.empty else pd.DataFrame()
    processed = table[table["processed_feature_ready"] == True] if not table.empty else pd.DataFrame()
    broken = table[
        table["contract_quality_label"].isin(["MISSING_REQUIRED_COLUMNS", "INVALID_DATA", "EMPTY_DATA", "UNKNOWN_CSV"])
    ] if not table.empty else pd.DataFrame()
    importers = pd.DataFrame(list_importers())
    lines = [
        "# Phase 12.2 Data Contract Audit",
        "",
        "Phase 12.1 Data Contract Audit compatibility retained.",
        "",
        "Diagnostic/foundation only. No tier rules, probability logic, recommended-market logic, betting, staking, or ROI logic changed.",
        "",
        "## A. Executive Summary",
        f"- CSV files scanned: {total}",
        f"- Historical replay-ready files: {len(replay)}",
        f"- Fixture-ready files: {len(fixtures)}",
        f"- Odds-ready files: {len(odds)}",
        f"- xG-ready files: {len(xg)}",
        f"- Template-only files: {len(templates)}",
        f"- Processed feature files: {len(processed)}",
        f"- Files requiring contract fixes: {len(broken)}",
        "",
        "## B. Historical Match Files Ready for Replay",
    ]
    lines += _section_table(replay, ["file_name", "file_type", "row_count", "available_odds_columns", "available_xg_columns", "contract_quality_label"])
    lines += ["## C. Fixture Files Ready for Daily Reports"]
    lines += _section_table(fixtures, ["file_name", "file_type", "row_count", "available_context_columns", "contract_quality_label"])
    lines += ["## D. Odds Files Ready for Enrichment"]
    lines += _section_table(odds, ["file_name", "file_type", "row_count", "available_odds_columns", "contract_quality_label"])
    lines += ["## E. xG Files Ready for Enrichment"]
    lines += _section_table(xg, ["file_name", "file_type", "row_count", "available_xg_columns", "contract_quality_label"])
    lines += ["## F. Template Files"]
    lines += _section_table(templates, ["file_name", "file_type", "row_count", "contract_quality_label"])
    lines += ["## G. Processed Feature Files"]
    lines += _section_table(processed, ["file_name", "file_type", "row_count", "available_context_columns", "contract_quality_label"])
    lines += ["## H. Files Still Requiring Contract Fixes"]
    lines += _section_table(broken, ["file_name", "file_type", "contract_type", "missing_contract_columns", "contract_quality_label"])
    lines += ["## I. Importer Registry Readiness"]
    lines += _section_table(importers, ["importer_id", "source_type", "status", "description"])
    lines += [
        "## J. Phase 12.2 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(root: Path = ROOT, output_dir: Path | None = None) -> tuple[pd.DataFrame, str]:
    output_dir = output_dir or (root / "outputs" / "diagnostics")
    output_dir.mkdir(parents=True, exist_ok=True)
    table = build_audit_table(root)
    rec = recommendation(table)
    markdown = build_markdown(table, rec)
    table.to_csv(output_dir / OUTPUT_CSV, index=False)
    (output_dir / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, markdown = run(root=Path(args.root), output_dir=Path(args.output_dir))
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(markdown.split("## J. Phase 12.2 Recommendation", 1)[-1].strip().splitlines()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
