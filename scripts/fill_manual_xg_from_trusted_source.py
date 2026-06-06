# -*- coding: utf-8 -*-
"""Fill a manual xG template preview from a trusted local xG source CSV."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.manual_xg_acceptance import evaluate_manual_xg_acceptance  # noqa: E402
from football_prediction_v19.importers.trusted_xg_source import build_filled_manual_xg_preview  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--template", required=True)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "xg_fill_preview"))
    parser.add_argument("--target", default=None)
    parser.add_argument("--manifest-output", default=None)
    parser.add_argument("--no-write", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    preview, summary = build_filled_manual_xg_preview(
        args.source,
        args.template,
        output_dir=args.output_dir,
        write_preview=not args.no_write,
    )
    acceptance_label = ""
    if args.target:
        target_df = pd.read_csv(args.target, low_memory=False)
        _joined, acceptance = evaluate_manual_xg_acceptance(
            preview,
            target_df=target_df,
            source_path=summary["output_path"] or args.template,
            target_path=args.target,
        )
        acceptance_label = acceptance.acceptance_label
    if args.manifest_output:
        Path(args.manifest_output).parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([{
            "xg_file_path": summary["output_path"],
            "target_file_path": args.target or "",
            "xg_source_schema": summary["xg_source_schema"],
            "rows_filled": summary["rows_filled"],
            "join_coverage_pct": summary["join_coverage_pct"],
            "acceptance_label": acceptance_label,
        }]).to_csv(args.manifest_output, index=False)
    print(f"rows_template={summary['rows_template']}")
    print(f"rows_filled={summary['rows_filled']}")
    print(f"rows_missing_xg={summary['rows_missing_xg']}")
    print(f"join_coverage_pct={summary['join_coverage_pct']}")
    if args.target:
        print(f"acceptance_label={acceptance_label}")
    print(f"output_path={summary['output_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
