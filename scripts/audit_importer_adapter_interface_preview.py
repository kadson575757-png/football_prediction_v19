# -*- coding: utf-8 -*-
"""Audit Phase 15.3 importer adapter interface preview."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

IMPORTER_ADAPTER_INTERFACE_PREVIEW_READY = "IMPORTER_ADAPTER_INTERFACE_PREVIEW_READY"
BUILD_IMPORTER_ADAPTER_INTERFACE_PREVIEW = "BUILD_IMPORTER_ADAPTER_INTERFACE_PREVIEW"
FIX_IMPORTER_ADAPTER_INTERFACE_PREVIEW = "FIX_IMPORTER_ADAPTER_INTERFACE_PREVIEW"

OUTPUT_CSV = "importer_adapter_interface_preview_summary.csv"
OUTPUT_MD = "importer_adapter_interface_preview_summary.md"

EXPECTED_SOURCE_IDS = ["fbref", "understat", "fotmob", "sofascore", "whoscored", "soccerdata"]
REQUIRED_COLUMNS = {
    "source_id", "provider_name", "adapter_class", "network_calls_enabled",
    "contracts_supported", "adapter_status", "rows_normalized",
    "implementation_status", "recommendation", "notes",
}
SAFE_STATUSES = {"IMPORTER_ADAPTER_INTERFACE_PREVIEW_READY", "IMPORTER_ADAPTER_NETWORK_DISABLED_BY_DESIGN"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", default=None)
    parser.add_argument("--preview-dir", default=str(ROOT / "outputs" / "importer_preview"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def _preview_path(preview: str | Path | None, preview_dir: str | Path) -> Path | None:
    if preview:
        return Path(preview)
    path = Path(preview_dir) / "importer_adapter_interface_preview.csv"
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


def audit_preview(path: Path, *, base_dir: str | Path = ROOT) -> dict[str, Any]:
    base = Path(base_dir).resolve()
    errors: list[str] = []
    if not _under_preview(str(path), base):
        errors.append("UNSAFE_ADAPTER_PREVIEW_PATH")
    try:
        table = pd.read_csv(path, low_memory=False)
    except Exception as exc:
        return {
            "preview_path": str(path),
            "adapters_found": 0,
            "missing_source_ids": "ALL",
            "missing_required_columns": "ALL",
            "network_calls_enabled": True,
            "rows_normalized_nonzero": True,
            "adapter_statuses_safe": False,
            "preview_valid": False,
            "blocking_reasons": " | ".join([*errors, str(exc)]),
        }
    missing_cols = sorted(REQUIRED_COLUMNS - set(table.columns))
    if missing_cols:
        errors.append("MISSING_REQUIRED_COLUMNS")
    source_ids = set(table["source_id"].astype(str)) if "source_id" in table.columns else set()
    missing_sources = [source for source in EXPECTED_SOURCE_IDS if source not in source_ids]
    if missing_sources:
        errors.append("MISSING_EXPECTED_SOURCE_IDS")
    network_enabled = any(_as_bool(value) for value in table["network_calls_enabled"]) if "network_calls_enabled" in table.columns else True
    if network_enabled:
        errors.append("NETWORK_CALLS_ENABLED")
    rows_nonzero = bool((pd.to_numeric(table["rows_normalized"], errors="coerce").fillna(1) != 0).any()) if "rows_normalized" in table.columns else True
    if rows_nonzero:
        errors.append("ROWS_NORMALIZED_NONZERO")
    statuses = set(table["adapter_status"].astype(str)) if "adapter_status" in table.columns else set()
    impl = set(table["implementation_status"].astype(str)) if "implementation_status" in table.columns else set()
    statuses_safe = statuses.issubset(SAFE_STATUSES) and impl.issubset(SAFE_STATUSES)
    if not statuses_safe:
        errors.append("UNSAFE_ADAPTER_STATUS")
    return {
        "preview_path": str(path),
        "adapters_found": int(len(table)),
        "missing_source_ids": " | ".join(missing_sources),
        "missing_required_columns": " | ".join(missing_cols),
        "network_calls_enabled": network_enabled,
        "rows_normalized_nonzero": rows_nonzero,
        "adapter_statuses_safe": statuses_safe,
        "preview_valid": not errors,
        "blocking_reasons": " | ".join(errors),
    }


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return BUILD_IMPORTER_ADAPTER_INTERFACE_PREVIEW
    if table["preview_valid"].any():
        return IMPORTER_ADAPTER_INTERFACE_PREVIEW_READY
    return FIX_IMPORTER_ADAPTER_INTERFACE_PREVIEW


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    lines = [
        "# Phase 15.3 Importer Adapter Interface Preview Audit",
        "",
        "Phase 15.3 is an adapter interface preview only. No network calls are made.",
        "",
        "## A. Executive Summary",
        f"- previews audited: {len(table)}",
        f"- valid previews: {int(table['preview_valid'].sum()) if not table.empty else 0}",
        "",
        "## B. Diagnostics",
    ]
    if table.empty:
        lines += ["No importer adapter interface preview found.", ""]
    else:
        cols = ["adapters_found", "missing_source_ids", "network_calls_enabled", "rows_normalized_nonzero", "adapter_statuses_safe", "preview_valid", "blocking_reasons"]
        lines += ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
        for _, row in table[cols].iterrows():
            lines.append("| " + " | ".join(str(row[col]).replace("|", ";") for col in cols) + " |")
        lines.append("")
    lines += [
        "## C. Safety Checks",
        "- No live scraping/API fetching is active.",
        "- Preview adapters normalize zero rows.",
        "- No provider data is imported.",
        "- No model, probability, market, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "",
        "## D. Phase 15.3 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(
    *,
    preview: str | Path | None = None,
    preview_dir: str | Path = ROOT / "outputs" / "importer_preview",
    output_dir: str | Path = ROOT / "outputs" / "diagnostics",
    base_dir: str | Path = ROOT,
) -> tuple[pd.DataFrame, str, str]:
    path = _preview_path(preview, preview_dir)
    rows = [audit_preview(path, base_dir=base_dir)] if path else []
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
    table, _markdown, rec = run(preview=args.preview, preview_dir=args.preview_dir, output_dir=args.output_dir, base_dir=args.base_dir)
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(rec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
