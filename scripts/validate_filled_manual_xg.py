# -*- coding: utf-8 -*-
"""Validate a filled manual xG CSV before production use."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.manual_xg_acceptance import run_manual_xg_acceptance_gate  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xg", required=True)
    parser.add_argument("--target", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "xg_acceptance_preview"))
    parser.add_argument("--min-join-coverage", type=float, default=95.0)
    parser.add_argument("--no-write-preview", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_manual_xg_acceptance_gate(
        args.xg,
        target_path=args.target,
        output_dir=args.output_dir,
        min_join_coverage=args.min_join_coverage,
        write_preview=not args.no_write_preview,
    )
    print(f"rows_source={result.rows_source}")
    print(f"rows_valid={result.rows_valid}")
    print(f"rows_invalid={result.rows_invalid}")
    print(f"rows_join_matched={result.rows_join_matched}")
    print(f"join_coverage_pct={result.join_coverage_pct}")
    print(f"acceptance_label={result.acceptance_label}")
    print(f"blocking_reasons={' | '.join(result.blocking_reasons)}")
    print(f"preview_output_path={result.preview_output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
