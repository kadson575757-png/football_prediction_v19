# -*- coding: utf-8 -*-
"""Build preview rows for the importer adapter interface.

No network calls are made. Preview adapters only validate configuration and
schema contract support.
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
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_importer_schema_contracts_preview import build_importer_schema_contracts_preview  # noqa: E402
from build_importer_source_registry_preview import build_importer_source_registry_preview  # noqa: E402
from football_prediction_v19.importers.adapter_interface import (  # noqa: E402
    BaseImporterAdapter,
    ImporterAdapterConfig,
    ImporterRunContext,
    IMPORTER_ADAPTER_INTERFACE_PREVIEW_READY,
    IMPORTER_ADAPTER_NOT_IMPLEMENTED,
)

IMPORTER_ADAPTER_INTERFACE_PREVIEW_BLOCKED_UNSAFE_PATH = "IMPORTER_ADAPTER_INTERFACE_PREVIEW_BLOCKED_UNSAFE_PATH"

OUTPUT_DIR = ROOT / "outputs" / "importer_preview"
OUTPUT_CSV = "importer_adapter_interface_preview.csv"
OUTPUT_MD = "importer_adapter_interface_preview.md"

ADAPTER_COLUMNS = [
    "source_id",
    "provider_name",
    "adapter_class",
    "network_calls_enabled",
    "contracts_supported",
    "adapter_status",
    "rows_normalized",
    "implementation_status",
    "recommendation",
    "notes",
]


class PreviewImporterAdapter(BaseImporterAdapter):
    def fetch_raw(self, context: ImporterRunContext) -> Any:
        raise NotImplementedError(IMPORTER_ADAPTER_NOT_IMPLEMENTED)

    def normalize(self, raw: Any, context: ImporterRunContext) -> Any:
        raise NotImplementedError(IMPORTER_ADAPTER_NOT_IMPLEMENTED)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default=str(OUTPUT_DIR / "importer_source_registry_preview.csv"))
    parser.add_argument("--contracts", default=str(OUTPUT_DIR / "importer_schema_contracts_preview.csv"))
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
        raise ValueError("IMPORTER_ADAPTER_OUTPUT_DIR_MUST_BE_UNDER_OUTPUTS_IMPORTER_PREVIEW")
    return resolved


def _ensure_inputs(registry: Path, contracts: Path, out_dir: Path, base: Path) -> tuple[Path, Path]:
    if not registry.exists():
        reg = build_importer_source_registry_preview(output_dir=out_dir, write_preview=True, base_dir=base)
        registry = Path(str(reg["registry_output_path"]))
    if not contracts.exists():
        con = build_importer_schema_contracts_preview(registry=registry, output_dir=out_dir, write_preview=True, base_dir=base)
        contracts = Path(str(con["contracts_output_path"]))
    return registry, contracts


def _contracts_for_source(_source_id: str, contracts_df: pd.DataFrame) -> tuple[str, ...]:
    return tuple(sorted(contracts_df["contract_id"].dropna().astype(str).unique()))


def build_adapter_rows(registry_df: pd.DataFrame, contracts_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for _, source in registry_df.iterrows():
        supported = _contracts_for_source(str(source["source_id"]), contracts_df)
        adapter = PreviewImporterAdapter(ImporterAdapterConfig(
            source_id=str(source["source_id"]),
            provider_name=str(source["provider_name"]),
            supported_contracts=supported,
            network_enabled=False,
        ))
        result = adapter.run_preview(ImporterRunContext(requested_contracts=supported))
        rows.append({
            "source_id": result.source_id,
            "provider_name": result.provider_name,
            "adapter_class": adapter.__class__.__name__,
            "network_calls_enabled": result.network_calls_enabled,
            "contracts_supported": " | ".join(result.contracts_supported),
            "adapter_status": result.adapter_status,
            "rows_normalized": result.rows_normalized,
            "implementation_status": "IMPORTER_ADAPTER_NETWORK_DISABLED_BY_DESIGN",
            "recommendation": result.recommendation,
            "notes": result.notes,
        })
    return pd.DataFrame(rows, columns=ADAPTER_COLUMNS)


def build_markdown(table: pd.DataFrame) -> str:
    lines = [
        "# Phase 15.3 Importer Adapter Interface Preview",
        "",
        "Phase 15.3 defines the adapter interface/base contract only.",
        "",
        "## A. Executive Summary",
        f"- adapters registered: {len(table)}",
        "- network calls enabled: false",
        "- provider adapters live: false",
        "",
        "## B. Adapter Rows",
        "| source_id | adapter_class | adapter_status | rows_normalized |",
        "| --- | --- | --- | --- |",
    ]
    for _, row in table.iterrows():
        lines.append(f"| {row['source_id']} | {row['adapter_class']} | {row['adapter_status']} | {row['rows_normalized']} |")
    lines += [
        "",
        "## C. Safety Notes",
        "- No provider adapters are live yet.",
        "- No network calls are made.",
        "- Future phases can implement one adapter at a time.",
        "- No model, probability, market, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "",
        "## D. Recommendation",
        IMPORTER_ADAPTER_INTERFACE_PREVIEW_READY,
        "",
    ]
    return "\n".join(lines)


def _blocked(status: str, reason: str) -> dict[str, Any]:
    return {
        "importer_adapter_interface_status": status,
        "adapters_registered": 0,
        "network_calls_enabled": False,
        "adapter_output_path": "",
        "adapter_summary_path": "",
        "recommendation": status,
        "blocking_reasons": reason,
    }


def build_importer_adapter_interface_preview(
    *,
    registry: str | Path = OUTPUT_DIR / "importer_source_registry_preview.csv",
    contracts: str | Path = OUTPUT_DIR / "importer_schema_contracts_preview.csv",
    output_dir: str | Path = OUTPUT_DIR,
    write_preview: bool = False,
    base_dir: str | Path = ROOT,
) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    try:
        out_dir = _safe_output_dir(output_dir, base)
    except ValueError as exc:
        return _blocked(IMPORTER_ADAPTER_INTERFACE_PREVIEW_BLOCKED_UNSAFE_PATH, str(exc))
    registry_path = Path(registry)
    if not registry_path.is_absolute():
        registry_path = base / registry_path
    contracts_path = Path(contracts)
    if not contracts_path.is_absolute():
        contracts_path = base / contracts_path
    registry_path, contracts_path = _ensure_inputs(registry_path, contracts_path, out_dir, base)
    table = build_adapter_rows(pd.read_csv(registry_path, low_memory=False), pd.read_csv(contracts_path, low_memory=False))
    csv_path = ""
    md_path = ""
    if write_preview:
        out_dir.mkdir(parents=True, exist_ok=True)
        csv_file = (out_dir / OUTPUT_CSV).resolve()
        md_file = (out_dir / OUTPUT_MD).resolve()
        if out_dir not in csv_file.parents or out_dir not in md_file.parents:
            return _blocked(IMPORTER_ADAPTER_INTERFACE_PREVIEW_BLOCKED_UNSAFE_PATH, "ADAPTER_OUTPUT_OUTSIDE_OUTPUT_DIR")
        table.to_csv(csv_file, index=False)
        md_file.write_text(build_markdown(table), encoding="utf-8")
        csv_path = str(csv_file)
        md_path = str(md_file)
    return {
        "importer_adapter_interface_status": IMPORTER_ADAPTER_INTERFACE_PREVIEW_READY,
        "adapters_registered": int(len(table)),
        "network_calls_enabled": False,
        "adapter_output_path": csv_path,
        "adapter_summary_path": md_path,
        "recommendation": IMPORTER_ADAPTER_INTERFACE_PREVIEW_READY,
        "blocking_reasons": "",
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_importer_adapter_interface_preview(registry=args.registry, contracts=args.contracts, output_dir=args.output_dir, write_preview=args.write_preview, base_dir=args.base_dir)
    for key in ["importer_adapter_interface_status", "adapters_registered", "network_calls_enabled", "adapter_output_path", "adapter_summary_path", "recommendation"]:
        print(f"{key}={str(summary[key]).lower() if key == 'network_calls_enabled' else summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
