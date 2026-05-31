# -*- coding: utf-8 -*-
"""Phase 12.7 partial xG source attribution audit.

Diagnostic/foundation only. No xG values are inferred, invented, deleted, or
modified.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from audit_data_contracts import discover_csv_files  # noqa: E402
from football_prediction_v19.xg_partial_attribution import (  # noqa: E402
    EMPTY_XG_COLUMNS_IN_PROCESSED_FEATURES,
    FBREF_IDENTITY_MAPPING_MISSING,
    REAL_XG_SOURCE_WITH_NULL_VALUES,
    SAMPLE_OR_DEMO_PARTIAL_XG,
    TEMPLATE_PARTIAL_XG,
    UNDERSTAT_IDENTITY_MAPPING_MISSING,
    build_partial_xg_attribution_for_files,
    summarize_partial_xg_attribution,
)

OUTPUT_CSV = "partial_xg_source_attribution_summary.csv"
OUTPUT_MD = "partial_xg_source_attribution_summary.md"


def build_table(root: Path) -> pd.DataFrame:
    return pd.DataFrame(build_partial_xg_attribution_for_files(discover_csv_files(root)))


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return "INCONCLUSIVE_NO_PARTIAL_XG_FILES"
    categories = set(table["partial_xg_source_category"].astype(str))
    if REAL_XG_SOURCE_WITH_NULL_VALUES in categories:
        return "ADD_MANUAL_XG_VALUES"
    if FBREF_IDENTITY_MAPPING_MISSING in categories:
        return "DEFINE_FBREF_XG_MAPPING"
    if UNDERSTAT_IDENTITY_MAPPING_MISSING in categories:
        return "DEFINE_UNDERSTAT_XG_MAPPING"
    non_blocking = set(table.loc[table["blocking"] == False, "partial_xg_source_category"].astype(str))
    if categories and categories == non_blocking:
        return "READY_FOR_XG_IMPORTER_SKELETONS"
    return "MANUAL_REVIEW_PARTIAL_XG"


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
    summary = summarize_partial_xg_attribution(table.to_dict("records") if not table.empty else [])
    blocking = table[table["blocking"] == True] if not table.empty else pd.DataFrame()
    non_blocking = table[table["blocking"] == False] if not table.empty else pd.DataFrame()
    processed_empty = table[table["partial_xg_source_category"] == EMPTY_XG_COLUMNS_IN_PROCESSED_FEATURES] if not table.empty else pd.DataFrame()
    real_null = table[table["partial_xg_source_category"] == REAL_XG_SOURCE_WITH_NULL_VALUES] if not table.empty else pd.DataFrame()
    templates = table[table["partial_xg_source_category"].isin([TEMPLATE_PARTIAL_XG, SAMPLE_OR_DEMO_PARTIAL_XG])] if not table.empty else pd.DataFrame()
    mapping = table[table["partial_xg_source_category"].isin([FBREF_IDENTITY_MAPPING_MISSING, UNDERSTAT_IDENTITY_MAPPING_MISSING])] if not table.empty else pd.DataFrame()
    lines = [
        "# Phase 12.7 Partial xG Source Attribution",
        "",
        "Phase 12.7 is diagnostic/foundation only. No xG values were inferred, invented, deleted, or modified.",
        "",
        "## A. Executive Summary",
        f"- Partial xG files: {len(table)}",
        f"- Blocking partial xG files: {len(blocking)}",
        f"- Non-blocking partial xG files: {len(non_blocking)}",
        f"- Processed files with empty xG columns: {len(processed_empty)}",
        f"- Real xG sources with null values: {len(real_null)}",
        f"- Template/sample partial xG files: {len(templates)}",
        f"- FBref mapping issues: {int((table['partial_xg_source_category'] == FBREF_IDENTITY_MAPPING_MISSING).sum()) if not table.empty else 0}",
        f"- Understat mapping issues: {int((table['partial_xg_source_category'] == UNDERSTAT_IDENTITY_MAPPING_MISSING).sum()) if not table.empty else 0}",
        "",
        "## B. Partial xG Attribution by Category",
    ]
    lines += _section_table(summary, ["partial_xg_source_category", "n", "row_count_total", "xg_null_total", "blocking_count", "decision_labels"])
    lines += ["## C. Blocking Partial xG Issues"]
    lines += _section_table(blocking, ["file_name", "file_type", "xg_contract_label", "partial_xg_source_category", "partial_xg_decision", "recommended_action"], limit=80)
    lines += ["## D. Empty xG Columns in Processed Feature Files"]
    lines += _section_table(processed_empty, ["file_name", "row_count", "xg_null_count", "partial_xg_decision", "recommended_action"], limit=80)
    lines += ["## E. Template / Sample Partial xG Files"]
    lines += _section_table(templates, ["file_name", "xg_contract_label", "partial_xg_source_category", "blocking"], limit=80)
    lines += ["## F. FBref / Understat Mapping Issues"]
    lines += _section_table(mapping, ["file_name", "partial_xg_source_category", "partial_xg_decision", "recommended_action"])
    lines += [
        "## G. Recommended Cleanup Plan",
        "- Do not delete columns automatically.",
        "- Do not invent xG values.",
        "- Decide whether empty xG columns are allowed placeholders or should be omitted from processed outputs.",
        "- Add production xG file later only via manual_xg_csv or a real importer.",
        "",
        "## G2. Empty xG Column Policy",
        "- Active policy: ALLOW_EMPTY_XG_PLACEHOLDERS",
        "- Empty xG placeholders are allowed but non-usable for model.",
        "- They do not count as production-ready xG.",
        "- They do not upgrade confidence/recommendations.",
        "",
        "## H. Phase 12.7 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(root: Path = ROOT, output_dir: Path | None = None) -> tuple[pd.DataFrame, str]:
    output_dir = output_dir or (root / "outputs" / "diagnostics")
    output_dir.mkdir(parents=True, exist_ok=True)
    table = build_table(root)
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
    print(markdown.split("## H. Phase 12.7 Recommendation", 1)[-1].strip().splitlines()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
