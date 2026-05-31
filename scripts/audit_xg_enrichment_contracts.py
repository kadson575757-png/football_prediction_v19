# -*- coding: utf-8 -*-
"""Phase 12.6 xG enrichment contract audit.

Diagnostic/foundation only. No xG values are inferred or invented.
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

from audit_data_contracts import discover_csv_files  # noqa: E402
from football_prediction_v19.csv_adapter_mapping import summarize_adapter_mapping  # noqa: E402
from football_prediction_v19.importers.registry import list_importers  # noqa: E402
from football_prediction_v19.xg_enrichment import (  # noqa: E402
    FBREF_XG_EXPORT,
    XG_CONTRACT_EMPTY,
    XG_CONTRACT_MISSING_IDENTITY,
    XG_CONTRACT_MISSING_XG_VALUES,
    XG_CONTRACT_PARTIAL,
    XG_CONTRACT_READY,
    summarize_xg_coverage,
)

OUTPUT_CSV = "xg_enrichment_audit_summary.csv"
OUTPUT_MD = "xg_enrichment_audit_summary.md"


def _safe_read(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, low_memory=False)
    except Exception:
        return pd.DataFrame()


def _join(value: Any) -> str:
    if isinstance(value, list):
        return " | ".join(str(item) for item in value)
    return str(value)


def audit_file(path: Path) -> dict[str, Any]:
    df = _safe_read(path)
    xg = summarize_xg_coverage(df, path=path)
    adapter = summarize_adapter_mapping(path, df)
    row = {
        "file_path": str(path),
        "file_name": path.name,
        **xg,
        "adapter_type": adapter["adapter_type"],
        "adapter_readiness": adapter["adapter_readiness"],
        "adapter_note": adapter["adapter_note"],
    }
    for key in ("available_identity_columns", "available_xg_columns", "missing_identity_columns", "missing_xg_columns"):
        row[key] = _join(row.get(key, []))
    return row


def build_audit_table(root: Path) -> pd.DataFrame:
    return pd.DataFrame([audit_file(path) for path in discover_csv_files(root)])


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return "INCONCLUSIVE_NO_XG_CANDIDATES"
    production_ready = table[table["xg_production_ready"] == True]
    contract_ready = table[table["xg_contract_ready"] == True]
    xg_candidate = (
        table["available_xg_columns"].astype(str).str.strip().ne("")
        | table["file_name"].astype(str).str.lower().str.contains("xg", na=False)
    )
    partial = table[
        table["xg_contract_label"].isin([XG_CONTRACT_PARTIAL, XG_CONTRACT_MISSING_IDENTITY, XG_CONTRACT_MISSING_XG_VALUES])
        & (table["xg_file_role"] != "TEMPLATE_OR_SAMPLE")
        & xg_candidate
    ]
    fbref_candidates = table[
        (table["adapter_type"].astype(str).str.contains("FBREF", na=False))
        | (table["xg_schema"] == FBREF_XG_EXPORT)
    ]
    has_xg_signal = table["available_xg_columns"].astype(str).str.strip().ne("").any()
    if not production_ready.empty:
        return "READY_FOR_XG_CSV_IMPORTER"
    if not partial.empty:
        return "FIX_PARTIAL_XG_FILES_FIRST"
    if not fbref_candidates.empty:
        return "DEFINE_FBREF_XG_MAPPING"
    if not contract_ready.empty:
        return "ADD_MANUAL_XG_CSV_FILES"
    if not has_xg_signal:
        return "ADD_MANUAL_XG_CSV_FILES"
    return "INCONCLUSIVE_NO_XG_CANDIDATES"


def _section_table(df: pd.DataFrame, columns: list[str], limit: int | None = None) -> list[str]:
    if df.empty:
        return ["No rows.", ""]
    if limit is not None:
        df = df.head(limit)
    cols = [col for col in columns if col in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in df[cols].iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in cols) + " |")
    lines.append("")
    return lines


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    ready = table[table["xg_contract_ready"] == True] if not table.empty else pd.DataFrame()
    production_ready = table[table["xg_production_ready"] == True] if not table.empty else pd.DataFrame()
    if not table.empty:
        xg_candidate = (
            table["available_xg_columns"].astype(str).str.strip().ne("")
            | table["file_name"].astype(str).str.lower().str.contains("xg", na=False)
        )
        partial = table[
            table["xg_contract_label"].isin([XG_CONTRACT_PARTIAL, XG_CONTRACT_MISSING_IDENTITY, XG_CONTRACT_MISSING_XG_VALUES])
            & (table["xg_file_role"] != "TEMPLATE_OR_SAMPLE")
            & xg_candidate
        ]
    else:
        partial = pd.DataFrame()
    empty = table[table["xg_contract_label"] == XG_CONTRACT_EMPTY] if not table.empty else pd.DataFrame()
    unsupported = table[~table.index.isin(ready.index.union(partial.index).union(empty.index))] if not table.empty else pd.DataFrame()
    fbref = table[
        (table["adapter_type"].astype(str).str.contains("FBREF", na=False))
        | (table["xg_schema"] == FBREF_XG_EXPORT)
    ] if not table.empty else pd.DataFrame()
    importers = pd.DataFrame([
        item for item in list_importers()
        if "xg" in item["importer_id"].lower() or "xg" in item["description"].lower()
    ])
    rows_with_xg = int(table.loc[table["available_xg_columns"].astype(str).str.strip().ne(""), "row_count"].sum()) if not table.empty else 0
    lines = [
        "# Phase 12.6 xG Enrichment Contract Audit",
        "",
        "Phase 12.6 is diagnostic/foundation only. No xG values were inferred or invented.",
        "",
        "## A. Executive Summary",
        f"- CSV files scanned: {len(table)}",
        f"- xG contract-ready files: {len(ready)}",
        f"- Production-ready xG files: {len(production_ready)}",
        f"- xG partial files: {len(partial)}",
        f"- xG unsupported files: {len(unsupported)}",
        f"- xG empty files: {len(empty)}",
        f"- Total rows with xG columns: {rows_with_xg}",
        f"- Total rows with missing/null xG: {int(table['xg_null_count'].sum()) if not table.empty else 0}",
        f"- Negative xG rows: {int(table['xg_negative_count'].sum()) if not table.empty else 0}",
        "",
        "## B. xG-Ready Files",
    ]
    lines += _section_table(ready, ["file_name", "xg_schema", "xg_file_role", "row_count", "available_identity_columns", "available_xg_columns", "xg_contract_ready", "xg_production_ready", "supported_for_enrichment"])
    lines += ["## B2. Production-Ready xG Files"]
    lines += _section_table(production_ready, ["file_name", "xg_schema", "row_count", "available_identity_columns", "available_xg_columns", "xg_production_ready"])
    lines += ["## C. Partial xG Files"]
    lines += _section_table(partial, ["file_name", "xg_schema", "xg_contract_label", "missing_identity_columns", "missing_xg_columns", "xg_null_count", "xg_negative_count"])
    lines += ["## D. FBref / Adapter-Mapped xG Candidates"]
    lines += _section_table(fbref, ["file_name", "adapter_type", "adapter_readiness", "xg_schema", "xg_contract_label", "available_xg_columns"])
    lines += ["## E. Unsupported / No xG Files"]
    lines += [
        f"Unsupported/no-xG files: {len(unsupported)}",
        "",
    ]
    lines += ["## F. Importer Registry xG Readiness"]
    lines += _section_table(importers, ["importer_id", "source_type", "status", "description"])
    lines += [
        "## G. Phase 12.6 Recommendation",
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
    print(markdown.split("## G. Phase 12.6 Recommendation", 1)[-1].strip().splitlines()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
