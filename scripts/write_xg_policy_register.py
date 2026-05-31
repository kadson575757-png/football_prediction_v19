# -*- coding: utf-8 -*-
"""Write the Phase 12.8 xG policy decision register."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.xg_policy import ALLOW_EMPTY_XG_PLACEHOLDERS  # noqa: E402

OUTPUT_CSV = "xg_policy_register.csv"
OUTPUT_MD = "xg_policy_register.md"


def build_rows() -> list[dict[str, str]]:
    return [
        {"section": "Policy Decision", "item": "Active policy", "value": ALLOW_EMPTY_XG_PLACEHOLDERS},
        {"section": "Allows", "item": "Empty xG columns", "value": "May remain in processed feature files as placeholders."},
        {"section": "Does Not Allow", "item": "Inferred xG", "value": "No xG values may be inferred, invented, deleted, or modified."},
        {"section": "Known Effects", "item": "Processed empty xG", "value": "Non-blocking placeholder; not production-ready and not usable for model."},
        {"section": "Next Work", "item": "Importer", "value": "Manual xG CSV importer skeleton or FBref mapping."},
    ]


def build_markdown(rows: list[dict[str, str]]) -> str:
    return "\n".join([
        "# Phase 12.8 xG Policy Register",
        "",
        "## A. Policy Decision",
        f"- Active policy: {ALLOW_EMPTY_XG_PLACEHOLDERS}",
        "",
        "## B. What This Allows",
        "- Empty xG columns may remain in processed feature files.",
        "- They are treated as placeholders.",
        "",
        "## C. What This Does Not Allow",
        "- No inferred xG values.",
        "- No confidence upgrades from empty xG columns.",
        "- No production-ready xG label unless real values are present.",
        "- No recommended-market upgrade.",
        "",
        "## D. Current Known Effects",
        "- Processed empty xG columns become non-blocking.",
        "- Real xG source null values still require manual/importer values.",
        "- FBref mapping still requires mapping work.",
        "",
        "## E. Safety Checks",
        "- No source CSV modified.",
        "- No xG values invented/deleted/modified.",
        "- No market_tier.py change.",
        "- No probability logic change.",
        "- No recommended market logic change.",
        "- No betting/staking/ROI change.",
        "- No SUPER_A_TIER activation.",
        "",
        "## F. Next Work",
        "- Manual xG CSV importer skeleton or FBref mapping.",
        "",
    ])


def run(output_dir: Path = ROOT / "outputs" / "diagnostics") -> tuple[pd.DataFrame, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    table = pd.DataFrame(build_rows())
    markdown = build_markdown(table.to_dict("records"))
    table.to_csv(output_dir / OUTPUT_CSV, index=False)
    (output_dir / OUTPUT_MD).write_text(markdown, encoding="utf-8")
    return table, markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    table, _markdown = run(output_dir=Path(args.output_dir))
    print(f"Wrote {len(table)} rows to {Path(args.output_dir) / OUTPUT_CSV}")
    print(ALLOW_EMPTY_XG_PLACEHOLDERS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
