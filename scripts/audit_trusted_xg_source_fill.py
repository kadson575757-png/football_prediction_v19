# -*- coding: utf-8 -*-
"""Phase 13.1 trusted xG source fill readiness audit."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.trusted_xg_source import (  # noqa: E402
    UNKNOWN_SCHEMA,
    build_filled_manual_xg_preview,
    detect_trusted_xg_source_schema,
)

OUTPUT_CSV = "trusted_xg_source_fill_summary.csv"
OUTPUT_MD = "trusted_xg_source_fill_summary.md"


def _unique(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if path.exists() and resolved not in seen:
            seen.add(resolved)
            out.append(path)
    return out


def discover_sources(root: Path) -> list[Path]:
    paths: list[Path] = []
    for pattern in (
        root / "data" / "raw" / "*xg*.csv",
        root / "data" / "manual_xg" / "*xg*.csv",
    ):
        paths.extend(sorted(pattern.parent.glob(pattern.name)) if pattern.parent.exists() else [])
    return _unique(paths)


def audit_source(path: Path, template: Path) -> dict[str, object]:
    try:
        df = pd.read_csv(path, low_memory=False)
        schema = detect_trusted_xg_source_schema(df)
        row = {
            "source_path": str(path),
            "source_file": path.name,
            "xg_source_schema": schema,
            "source_valid": schema != UNKNOWN_SCHEMA,
            "rows_template": 0,
            "rows_filled": 0,
            "rows_missing_xg": 0,
            "join_coverage_pct": 0.0,
            "fill_preview_ready": False,
            "error": "",
        }
        if schema != UNKNOWN_SCHEMA and template.exists():
            _preview, summary = build_filled_manual_xg_preview(path, template, write_preview=False)
            row.update(summary)
            row["fill_preview_ready"] = summary["rows_filled"] > 0
        return row
    except Exception as exc:
        return {
            "source_path": str(path),
            "source_file": path.name,
            "xg_source_schema": "",
            "source_valid": False,
            "rows_template": 0,
            "rows_filled": 0,
            "rows_missing_xg": 0,
            "join_coverage_pct": 0.0,
            "fill_preview_ready": False,
            "error": str(exc),
        }


def recommendation(table: pd.DataFrame) -> str:
    if table.empty:
        return "ADD_TRUSTED_XG_SOURCE_FILE"
    if table["fill_preview_ready"].any():
        full = table[(table["fill_preview_ready"] == True) & (table["rows_missing_xg"] == 0)]
        if not full.empty:
            return "READY_FOR_ACCEPTANCE_GATE"
        return "READY_TO_FILL_MANUAL_XG_FROM_TRUSTED_SOURCE"
    if table["source_valid"].any():
        return "READY_TO_FILL_MANUAL_XG_FROM_TRUSTED_SOURCE"
    return "FIX_TRUSTED_XG_SOURCE_SCHEMA"


def _section_table(df: pd.DataFrame, columns: list[str], limit: int = 40) -> list[str]:
    if df.empty:
        return ["No rows.", ""]
    cols = [col for col in columns if col in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in df[cols].head(limit).iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", ";") for col in cols) + " |")
    lines.append("")
    return lines


def build_markdown(table: pd.DataFrame, rec: str) -> str:
    ready = table[table["fill_preview_ready"] == True] if not table.empty else pd.DataFrame()
    invalid = table[table["source_valid"] == False] if not table.empty else pd.DataFrame()
    lines = [
        "# Phase 13.1 Trusted xG Source Fill Audit",
        "",
        "Phase 13.1 is foundation only. xG values are copied only from trusted local CSVs; no xG is inferred or invented.",
        "",
        "## A. Executive Summary",
        f"- trusted source candidates scanned: {len(table)}",
        f"- valid source schemas: {int(table['source_valid'].sum()) if not table.empty else 0}",
        f"- fill-preview-ready sources: {len(ready)}",
        f"- invalid sources: {len(invalid)}",
        "",
        "## B. Fill-Preview Ready Sources",
    ]
    cols = ["source_file", "xg_source_schema", "rows_template", "rows_filled", "rows_missing_xg", "join_coverage_pct"]
    lines += _section_table(ready, cols)
    lines += ["## C. Invalid / Unsupported Sources"]
    lines += _section_table(invalid, ["source_file", "xg_source_schema", "error"])
    lines += [
        "## D. Safety Checks",
        "- No source or template CSV modified.",
        "- No xG values inferred, invented, scraped, or pulled from APIs.",
        "- No model, probability, recommended-market, betting, staking, ROI, or SUPER_A_TIER logic changed.",
        "",
        "## E. Phase 13.1 Recommendation",
        rec,
        "",
    ]
    return "\n".join(lines)


def run(root: Path = ROOT, output_dir: Path | None = None) -> tuple[pd.DataFrame, str]:
    output_dir = output_dir or (root / "outputs" / "diagnostics")
    output_dir.mkdir(parents=True, exist_ok=True)
    template = root / "data" / "templates" / "manual_xg_template.csv"
    table = pd.DataFrame([audit_source(path, template) for path in discover_sources(root)])
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
    print(markdown.split("## E. Phase 13.1 Recommendation", 1)[-1].strip().splitlines()[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
