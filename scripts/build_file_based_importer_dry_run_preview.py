# -*- coding: utf-8 -*-
"""Build Phase 15.4 file-based importer dry-run preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_importer_schema_contracts_preview import build_importer_schema_contracts_preview  # noqa: E402
from football_prediction_v19.importers.file_based_importer import (  # noqa: E402
    FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_UNSAFE_PATH,
    FILE_BASED_IMPORTER_DRY_RUN_READY,
    FileBasedImporterAdapter,
    FileBasedImporterConfig,
)

OUTPUT_DIR = ROOT / "outputs" / "importer_preview"
OUTPUT_CSV = "file_based_importer_dry_run_preview.csv"
OUTPUT_MD = "file_based_importer_dry_run_preview.md"

SUMMARY_COLUMNS = [
    "source_id",
    "contract_id",
    "input_path",
    "output_path",
    "rows_input",
    "rows_normalized",
    "missing_required_columns",
    "network_calls_enabled",
    "dry_run_status",
    "recommendation",
    "notes",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=None)
    parser.add_argument("--contract-id", default="canonical_match")
    parser.add_argument("--source-id", default="file_csv")
    parser.add_argument("--contracts", default=str(OUTPUT_DIR / "importer_schema_contracts_preview.csv"))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--write-preview", action="store_true")
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _safe_output_dir(output_dir: str | Path, base_dir: Path) -> Path | None:
    out = Path(output_dir)
    if not out.is_absolute():
        out = base_dir / out
    resolved = out.resolve()
    allowed = (base_dir / "outputs" / "importer_preview").resolve()
    if resolved == allowed or allowed in resolved.parents:
        return resolved
    return None


def _tiny_fixture(path: Path, contract_id: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if contract_id == "canonical_xg_source":
        rows = [{
            "source_id": "file_csv",
            "provider_match_id": "fixture-1",
            "home_team": "Home FC",
            "away_team": "Away FC",
            "date": "2024-08-23",
            "home_xg": 1.2,
            "away_xg": 0.8,
            "xg_provider": "local_fixture",
            "xg_access_label": "dry_run_fixture",
        }]
    elif contract_id == "canonical_fixture":
        rows = [{
            "source_id": "file_csv",
            "provider_match_id": "fixture-1",
            "league": "Preview League",
            "season": "2024",
            "date": "2024-08-23",
            "home_team": "Home FC",
            "away_team": "Away FC",
            "fixture_status": "scheduled",
        }]
    else:
        rows = [{
            "source_id": "file_csv",
            "provider_match_id": "fixture-1",
            "league": "Preview League",
            "season": "2024",
            "date": "2024-08-23",
            "home_team": "Home FC",
            "away_team": "Away FC",
            "home_goals": 2,
            "away_goals": 1,
            "match_status": "finished",
        }]
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def _ensure_contracts(contracts: Path, output_dir: Path, base: Path) -> Path:
    if contracts.exists():
        return contracts
    summary = build_importer_schema_contracts_preview(output_dir=output_dir, write_preview=True, base_dir=base)
    return Path(str(summary["contracts_output_path"]))


def _markdown(table: pd.DataFrame) -> str:
    row = table.iloc[0] if not table.empty else {}
    lines = [
        "# Phase 15.4 File-Based Importer Dry Run Preview",
        "",
        "Phase 15.4 validates local CSV files against canonical importer contracts. No live network scraping or API fetching is active.",
        "",
        "## A. Executive Summary",
        f"- file importer status: {row.get('dry_run_status', '')}",
        f"- contract_id: {row.get('contract_id', '')}",
        f"- rows input: {row.get('rows_input', 0)}",
        f"- rows normalized: {row.get('rows_normalized', 0)}",
        "- network calls enabled: false",
        "",
        "## B. Dry Run Output",
        "| source_id | contract_id | rows_input | rows_normalized | dry_run_status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for _, item in table.iterrows():
        lines.append(f"| {item['source_id']} | {item['contract_id']} | {item['rows_input']} | {item['rows_normalized']} | {item['dry_run_status']} |")
    lines += [
        "",
        "## C. Safety Notes",
        "- Local CSV files are read only.",
        "- Normalized preview files are written only under outputs/importer_preview when requested.",
        "- Missing values are not inferred or invented.",
        "- Importer outputs stay separate from model integration until a later explicit phase.",
        "- No model, probability, market, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "",
        "## D. Recommendation",
        str(row.get("recommendation", "")),
        "",
    ]
    return "\n".join(lines)


def build_file_based_importer_dry_run_preview(
    *,
    input_path: str | Path | None = None,
    contract_id: str = "canonical_match",
    source_id: str = "file_csv",
    contracts: str | Path = OUTPUT_DIR / "importer_schema_contracts_preview.csv",
    output_dir: str | Path = OUTPUT_DIR,
    write_preview: bool = False,
    base_dir: str | Path = ROOT,
) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    out_dir = _safe_output_dir(output_dir, base)
    if out_dir is None:
        return {
            "file_importer_status": FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_UNSAFE_PATH,
            "contract_id": contract_id,
            "rows_input": 0,
            "rows_normalized": 0,
            "network_calls_enabled": False,
            "normalized_output_path": "",
            "preview_output_path": "",
            "preview_summary_path": "",
            "recommendation": FILE_BASED_IMPORTER_DRY_RUN_BLOCKED_UNSAFE_PATH,
        }
    contracts_path = Path(contracts)
    if not contracts_path.is_absolute():
        contracts_path = base / contracts_path
    contracts_path = _ensure_contracts(contracts_path, out_dir, base)
    if input_path is None:
        input_path = _tiny_fixture(out_dir / "runtime" / f"{contract_id}_tiny_fixture.csv", contract_id)

    adapter = FileBasedImporterAdapter(FileBasedImporterConfig(
        source_id=source_id,
        contract_id=contract_id,
        input_path=input_path,
        contracts_path=contracts_path,
        output_dir=out_dir,
        write_preview=write_preview,
        base_dir=base,
    ))
    result, _normalized = adapter.run_dry_run()
    table = pd.DataFrame([result.__dict__], columns=SUMMARY_COLUMNS)
    preview_path = ""
    summary_path = ""
    if write_preview:
        out_dir.mkdir(parents=True, exist_ok=True)
        csv_file = (out_dir / OUTPUT_CSV).resolve()
        md_file = (out_dir / OUTPUT_MD).resolve()
        table.to_csv(csv_file, index=False)
        md_file.write_text(_markdown(table), encoding="utf-8")
        preview_path = str(csv_file)
        summary_path = str(md_file)
    return {
        "file_importer_status": result.dry_run_status,
        "contract_id": result.contract_id,
        "rows_input": result.rows_input,
        "rows_normalized": result.rows_normalized,
        "network_calls_enabled": False,
        "normalized_output_path": result.output_path,
        "preview_output_path": preview_path,
        "preview_summary_path": summary_path,
        "recommendation": result.recommendation,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_file_based_importer_dry_run_preview(
        input_path=args.input,
        contract_id=args.contract_id,
        source_id=args.source_id,
        contracts=args.contracts,
        output_dir=args.output_dir,
        write_preview=args.write_preview,
        base_dir=args.base_dir,
    )
    for key in ["file_importer_status", "contract_id", "rows_input", "rows_normalized", "network_calls_enabled", "normalized_output_path", "recommendation"]:
        print(f"{key}={str(summary[key]).lower() if key == 'network_calls_enabled' else summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

