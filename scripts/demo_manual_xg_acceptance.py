# -*- coding: utf-8 -*-
"""Run the Phase 12.13 fake-data manual xG acceptance demo."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.manual_xg_acceptance import run_manual_xg_acceptance_gate  # noqa: E402

DEMO_XG = ROOT / "data" / "examples" / "manual_xg_accepted_demo.csv"
DEMO_TARGET = ROOT / "data" / "examples" / "manual_xg_acceptance_target_demo.csv"
OUTPUT_CSV = "manual_xg_acceptance_demo_summary.csv"
OUTPUT_MD = "manual_xg_acceptance_demo_summary.md"


def _section_table(df: pd.DataFrame, columns: list[str]) -> list[str]:
    cols = [col for col in columns if col in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for _, row in df[cols].iterrows():
        lines.append("| " + " | ".join(str(row.get(col, "")) for col in cols) + " |")
    lines.append("")
    return lines


def build_markdown(table: pd.DataFrame) -> str:
    row = table.iloc[0].to_dict()
    lines = [
        "# Phase 12.13 Manual xG Acceptance Demo",
        "",
        "Phase 12.13 demo uses fake demo xG values. These are not real match xG values and must not be used as production data.",
        "",
        "## A. Demo Summary",
        f"- acceptance_label: {row['acceptance_label']}",
        f"- rows_valid: {row['rows_valid']}",
        f"- rows_invalid: {row['rows_invalid']}",
        f"- join_coverage_pct: {row['join_coverage_pct']}",
        "",
        "## B. Input Files",
        f"- xG demo file: {row['source_path']}",
        f"- target demo file: {row['target_path']}",
        "",
        "## C. Acceptance Result",
    ]
    lines += _section_table(table, ["rows_source", "rows_valid", "rows_invalid", "acceptance_label", "blocking_reasons"])
    lines += ["## D. Join Coverage"]
    lines += _section_table(table, ["rows_join_matched", "join_coverage_pct", "preview_output_path"])
    lines += [
        "## E. Safety Checks",
        "- No source or target CSV modified.",
        "- No real xG values inferred, invented, filled, deleted, or written back.",
        "- No web/API/credential, betting, staking, ROI, probability, market-tier, or recommended-market logic changed.",
        "",
        "## F. Demo Caveat",
        "The demo CSV files use DEMO_ONLY fake values. They are excluded from broad production audits unless explicitly passed to this demo or validation scripts.",
        "",
    ]
    return "\n".join(lines)


def run(root: Path = ROOT, output_dir: Path | None = None) -> tuple[pd.DataFrame, str]:
    output_dir = output_dir or (root / "outputs" / "diagnostics")
    output_dir.mkdir(parents=True, exist_ok=True)
    result = run_manual_xg_acceptance_gate(
        root / "data" / "examples" / "manual_xg_accepted_demo.csv",
        target_path=root / "data" / "examples" / "manual_xg_acceptance_target_demo.csv",
        output_dir=root / "outputs" / "xg_acceptance_preview",
    )
    row = result.to_dict()
    row["blocking_reasons"] = " | ".join(result.blocking_reasons)
    row["warning_notes"] = " | ".join(result.warning_notes)
    table = pd.DataFrame([row])
    markdown = build_markdown(table)
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
    table, _markdown = run(root=Path(args.root), output_dir=Path(args.output_dir))
    print(str(table.iloc[0]["acceptance_label"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
