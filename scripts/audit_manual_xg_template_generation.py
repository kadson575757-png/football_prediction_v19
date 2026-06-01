# -*- coding: utf-8 -*-
"""Phase 12.11 manual xG entry template generation audit."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.manual_xg_template_generator import (  # noqa: E402
    XG_ENTRY_TEMPLATE_READY,
    XG_ENTRY_TEMPLATE_READY_WITH_WARNINGS,
    build_manual_xg_entry_template,
)

OUTPUT_CSV = "manual_xg_template_generation_summary.csv"
OUTPUT_MD = "manual_xg_template_generation_summary.md"


def _unique(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if path.exists() and resolved not in seen:
            seen.add(resolved)
            out.append(path)
    return out


def discover_template_sources(root: Path) -> list[Path]:
    paths: list[Path] = []
    for pattern in (
        root / "data" / "processed" / "real_matches_clean.csv",
        root / "data" / "processed" / "matches_clean_with_totals.csv",
        root / "data" / "processed" / "*_clean.csv",
        root / "data" / "upcoming*_fixtures*.csv",
        root / "data" / "*.csv",
    ):
        paths.extend(sorted(pattern.parent.glob(pattern.name)) if pattern.parent.exists() else [])
    return _unique(paths)


def audit_source(path: Path) -> dict[str, object]:
    try:
        df = pd.read_csv(path, low_memory=False)
        _template, result = build_manual_xg_entry_template(df, source_path=path)
        row = result.to_dict()
    except Exception as exc:
        row = {
            "source_path": str(path),
            "output_path": "",
            "rows_source": 0,
            "rows_template": 0,
            "duplicate_keys_removed": 0,
            "missing_identity_rows": 0,
            "template_quality_label": "XG_ENTRY_TEMPLATE_INVALID_SOURCE",
            "warning_notes": [str(exc)],
        }
    row["source_file"] = path.name
    row["warning_notes"] = " | ".join(row.get("warning_notes", []))
    row["recommended_command"] = (
        f"python scripts/generate_manual_xg_template.py --source {path.as_posix()} "
        "--output-dir outputs/xg_entry_templates"
    )
    return row


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return "INCONCLUSIVE_NO_TEMPLATE_SOURCES"
    ready = table["template_quality_label"].isin([XG_ENTRY_TEMPLATE_READY, XG_ENTRY_TEMPLATE_READY_WITH_WARNINGS])
    if ready.any():
        return "READY_TO_GENERATE_MANUAL_XG_ENTRY_TEMPLATE"
    if not table.empty:
        return "FIX_TEMPLATE_SOURCE_IDENTITY_COLUMNS"
    return "INCONCLUSIVE_NO_TEMPLATE_SOURCES"


def _section_table(df: pd.DataFrame, columns: list[str], limit: int = 30) -> list[str]:
    if df.empty:
        return ["No rows.", ""]
    cols = [col for col in columns if col in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in df[cols].head(limit).iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in cols) + " |")
    lines.append("")
    return lines


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    ready = table[table["template_quality_label"] == XG_ENTRY_TEMPLATE_READY] if not table.empty else pd.DataFrame()
    warn = table[table["template_quality_label"] == XG_ENTRY_TEMPLATE_READY_WITH_WARNINGS] if not table.empty else pd.DataFrame()
    invalid = table[~table["template_quality_label"].isin([XG_ENTRY_TEMPLATE_READY, XG_ENTRY_TEMPLATE_READY_WITH_WARNINGS])] if not table.empty else pd.DataFrame()
    useful = pd.concat([ready, warn], ignore_index=True) if not ready.empty or not warn.empty else pd.DataFrame()
    lines = [
        "# Phase 12.11 Manual xG Template Generation Audit",
        "",
        "Phase 12.11 is diagnostic/foundation only. No xG values were inferred or invented.",
        "",
        "## A. Executive Summary",
        f"- source files scanned: {len(table)}",
        f"- template-ready sources: {len(ready)}",
        f"- ready-with-warning sources: {len(warn)}",
        f"- invalid sources: {len(invalid)}",
        f"- total possible xG entry rows: {int(table['rows_template'].sum()) if not table.empty else 0}",
        "",
        "## B. Template-Ready Sources",
    ]
    cols = ["source_file", "rows_source", "rows_template", "duplicate_keys_removed", "missing_identity_rows", "template_quality_label"]
    lines += _section_table(ready, cols)
    lines += ["## C. Ready With Warnings"]
    lines += _section_table(warn, cols + ["warning_notes"])
    lines += ["## D. Invalid Sources"]
    lines += _section_table(invalid, ["source_file", "rows_source", "template_quality_label", "warning_notes"])
    lines += ["## E. Recommended Template Generation Commands"]
    if useful.empty:
        lines += ["No commands available until source identity columns are fixed.", ""]
    else:
        for command in useful["recommended_command"].head(10):
            lines.append(f"- `{command}`")
        lines.append("")
    lines += [
        "## F. Safety Checks",
        "- No source CSV modified.",
        "- Generated templates keep home_xg and away_xg blank for manual entry.",
        "- No xG values inferred or invented.",
        "- No web/API/credential, betting, staking, ROI, probability, market-tier, or recommended-market logic changed.",
        "",
        "## G. Phase 12.11 Recommendation",
        rec,
        "",
        "If templates are generated, the next step is still ADD_PRODUCTION_MANUAL_XG_FILE after values are filled manually.",
        "",
    ]
    return "\n".join(lines)


def run(root: Path = ROOT, output_dir: Path | None = None) -> tuple[pd.DataFrame, str]:
    output_dir = output_dir or (root / "outputs" / "diagnostics")
    output_dir.mkdir(parents=True, exist_ok=True)
    table = pd.DataFrame([audit_source(path) for path in discover_template_sources(root)])
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
    print(markdown.split("## G. Phase 12.11 Recommendation", 1)[-1].strip().splitlines()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
