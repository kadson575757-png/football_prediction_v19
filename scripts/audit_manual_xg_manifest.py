# -*- coding: utf-8 -*-
"""Phase 12.14 manual xG manifest acceptance register audit."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.manual_xg_manifest import (  # noqa: E402
    evaluate_manifest_acceptance,
    write_manifest_acceptance_register,
)

OUTPUT_CSV = "manual_xg_manifest_acceptance_register.csv"
OUTPUT_MD = "manual_xg_manifest_acceptance_register.md"


def _section_table(df: pd.DataFrame, columns: list[str], limit: int = 50) -> list[str]:
    if df.empty:
        return ["No rows.", ""]
    cols = [col for col in columns if col in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in df[cols].head(limit).iterrows():
        values = [str(row.get(col, "")).replace("|", ";") for col in cols]
        lines.append("| " + " | ".join(values) + " |")
    lines.append("")
    return lines


def build_markdown(table: pd.DataFrame, summary) -> str:
    accepted = table[table["production_accepted"] == True] if not table.empty else pd.DataFrame()
    rejected = table[(table["is_production_entry"] == True) & (table["production_accepted"] == False)] if not table.empty else pd.DataFrame()
    demos = table[table["is_demo"] == True] if not table.empty else pd.DataFrame()
    invalid = table[table["entry_valid"] == False] if not table.empty else pd.DataFrame()
    cols = [
        "manifest_id",
        "xg_file_path",
        "target_file_path",
        "acceptance_label",
        "rows_valid",
        "rows_join_matched",
        "join_coverage_pct",
        "entry_errors",
        "entry_warnings",
    ]
    lines = [
        "# Phase 12.14 Manual xG Manifest Acceptance Register",
        "",
        "Phase 12.14 is diagnostic/foundation only. Demo entries are never counted as production manual xG.",
        "",
        "## A. Executive Summary",
        f"- manifest path: {summary.manifest_path}",
        f"- entries total: {summary.entries_total}",
        f"- valid entries: {summary.entries_valid}",
        f"- invalid entries: {summary.entries_invalid}",
        f"- demo entries: {summary.demo_entries}",
        f"- production entries: {summary.production_entries}",
        f"- accepted production entries: {summary.accepted_production_entries}",
        f"- rejected production entries: {summary.rejected_production_entries}",
        "",
        "## B. Accepted Production Manual xG Entries",
    ]
    lines += _section_table(accepted, cols)
    lines += ["## C. Rejected Production Manual xG Entries"]
    lines += _section_table(rejected, cols)
    lines += ["## D. Demo Entries"]
    lines += _section_table(demos, cols + ["data_role", "is_demo"])
    lines += ["## E. Incomplete / Invalid Manifest Entries"]
    lines += _section_table(invalid, ["manifest_id", "data_role", "is_demo", "entry_errors", "notes"])
    lines += [
        "## F. Safety Checks",
        "- No manifest, xG source, or target CSV modified.",
        "- Demo entries are never counted as production manual xG.",
        "- No xG values inferred, invented, filled, deleted, or written back.",
        "- No web/API/credential, betting, staking, ROI, probability, market-tier, or recommended-market logic changed.",
        "",
        "## G. Phase 12.14 Recommendation",
        summary.recommendation,
        "",
        "Trusted xG promotion previews can generate manifest-entry previews but do not modify the manifest automatically.",
        "",
    ]
    return "\n".join(lines)


def run(
    manifest: Path = ROOT / "data" / "templates" / "manual_xg_manifest_template.csv",
    output_dir: Path | None = None,
    base_dir: Path = ROOT,
    *,
    include_demo: bool = False,
) -> tuple[pd.DataFrame, str]:
    output_dir = output_dir or (base_dir / "outputs" / "diagnostics")
    output_dir.mkdir(parents=True, exist_ok=True)
    table, summary = evaluate_manifest_acceptance(
        manifest,
        base_dir=base_dir,
        output_dir=base_dir / "outputs" / "xg_acceptance_preview",
        include_demo=include_demo,
    )
    write_manifest_acceptance_register(table, output_dir=output_dir)
    markdown = build_markdown(table, summary)
    (output_dir / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=str(ROOT / "data" / "templates" / "manual_xg_manifest_template.csv"))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    parser.add_argument("--base-dir", default=str(ROOT))
    parser.add_argument("--include-demo", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, markdown = run(
        manifest=Path(args.manifest),
        output_dir=Path(args.output_dir),
        base_dir=Path(args.base_dir),
        include_demo=args.include_demo,
    )
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(markdown.split("## G. Phase 12.14 Recommendation", 1)[-1].strip().splitlines()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
