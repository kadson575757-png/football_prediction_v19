# -*- coding: utf-8 -*-
"""Audit Phase 15.1 importer source registry previews."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

IMPORTER_SOURCE_REGISTRY_PREVIEW_READY = "IMPORTER_SOURCE_REGISTRY_PREVIEW_READY"
BUILD_IMPORTER_SOURCE_REGISTRY_PREVIEW = "BUILD_IMPORTER_SOURCE_REGISTRY_PREVIEW"
FIX_IMPORTER_SOURCE_REGISTRY_PREVIEW = "FIX_IMPORTER_SOURCE_REGISTRY_PREVIEW"

OUTPUT_CSV = "importer_source_registry_preview_summary.csv"
OUTPUT_MD = "importer_source_registry_preview_summary.md"

EXPECTED_SOURCE_IDS = ["fbref", "understat", "fotmob", "sofascore", "whoscored", "soccerdata"]
PREVIEW_ONLY_STATUSES = {"IMPORTER_SOURCE_NETWORK_DISABLED_BY_DESIGN", "IMPORTER_SOURCE_CONTRACT_PENDING", "IMPORTER_SOURCE_REGISTERED"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", default=None)
    parser.add_argument("--preview-dir", default=str(ROOT / "outputs" / "importer_preview"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _registry_path(registry: str | Path | None, preview_dir: str | Path) -> Path | None:
    if registry:
        return Path(registry)
    path = Path(preview_dir) / "importer_source_registry_preview.csv"
    return path if path.exists() else None


def _under_importer_preview(path_text: str, base: Path) -> bool:
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


def audit_registry(path: Path, *, base_dir: str | Path = ROOT) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    errors: list[str] = []
    if not _under_importer_preview(str(path), base):
        errors.append("UNSAFE_REGISTRY_PATH")
    try:
        table = pd.read_csv(path, low_memory=False)
    except Exception as exc:
        return {
            "registry_path": str(path),
            "sources_found": 0,
            "missing_source_ids": "ALL",
            "network_required_column_present": False,
            "network_calls_enabled": True,
            "preview_only_statuses": False,
            "registry_valid": False,
            "blocking_reasons": " | ".join([*errors, str(exc)]),
        }
    required_cols = {"source_id", "network_required", "network_calls_enabled", "implementation_status"}
    if not required_cols.issubset(table.columns):
        errors.append("MISSING_REQUIRED_COLUMNS")
    source_ids = set(table["source_id"].astype(str)) if "source_id" in table.columns else set()
    missing = [source for source in EXPECTED_SOURCE_IDS if source not in source_ids]
    if missing:
        errors.append("MISSING_EXPECTED_SOURCE_IDS")
    network_enabled = False
    if "network_calls_enabled" in table.columns:
        network_enabled = any(_as_bool(value) for value in table["network_calls_enabled"])
        if network_enabled:
            errors.append("NETWORK_CALLS_ENABLED")
    preview_only = False
    if "implementation_status" in table.columns:
        statuses = set(table["implementation_status"].astype(str))
        preview_only = statuses.issubset(PREVIEW_ONLY_STATUSES)
        if not preview_only:
            errors.append("NON_PREVIEW_IMPLEMENTATION_STATUS")
    return {
        "registry_path": str(path),
        "sources_found": int(len(table)),
        "missing_source_ids": " | ".join(missing),
        "network_required_column_present": "network_required" in table.columns,
        "network_calls_enabled": network_enabled,
        "preview_only_statuses": preview_only,
        "registry_valid": not errors,
        "blocking_reasons": " | ".join(errors),
    }


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return BUILD_IMPORTER_SOURCE_REGISTRY_PREVIEW
    if table["registry_valid"].any():
        return IMPORTER_SOURCE_REGISTRY_PREVIEW_READY
    return FIX_IMPORTER_SOURCE_REGISTRY_PREVIEW


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    lines = [
        "# Phase 15.1 Importer Source Registry Preview Audit",
        "",
        "Phase 15.1 is a registry/adapter contract preview only. No network calls are made.",
        "",
        "## A. Executive Summary",
        f"- registries audited: {len(table)}",
        f"- valid registries: {int(table['registry_valid'].sum()) if not table.empty else 0}",
        "",
        "## B. Registry Diagnostics",
    ]
    if table.empty:
        lines += ["No importer source registry preview found.", ""]
    else:
        cols = ["sources_found", "missing_source_ids", "network_required_column_present", "network_calls_enabled", "preview_only_statuses", "registry_valid", "blocking_reasons"]
        lines += ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
        for _, row in table[cols].iterrows():
            lines.append("| " + " | ".join(str(row[col]).replace("|", ";") for col in cols) + " |")
        lines.append("")
    lines += [
        "## C. Safety Checks",
        "- No live network access is enabled.",
        "- No scraping calls are active.",
        "- Implementation statuses remain preview/contract-only.",
        "- No model, probability, market, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "",
        "## D. Phase 15.1 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(
    *,
    registry: str | Path | None = None,
    preview_dir: str | Path = ROOT / "outputs" / "importer_preview",
    output_dir: str | Path = ROOT / "outputs" / "diagnostics",
    base_dir: str | Path = ROOT,
) -> tuple[pd.DataFrame, str, str]:
    path = _registry_path(registry, preview_dir)
    rows = [audit_registry(path, base_dir=base_dir)] if path else []
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
    table, _markdown, rec = run(registry=args.registry, preview_dir=args.preview_dir, output_dir=args.output_dir, base_dir=args.base_dir)
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
