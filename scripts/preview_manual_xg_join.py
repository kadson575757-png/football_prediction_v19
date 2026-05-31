# -*- coding: utf-8 -*-
"""Preview a manual xG CSV join against a target CSV."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.xg_join_preview import run_xg_join_preview  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xg", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--target-type", default="auto")
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "xg_join_preview"))
    parser.add_argument("--no-write-preview", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_xg_join_preview(
        args.xg,
        args.target,
        output_dir=args.output_dir,
        target_type=args.target_type,
        write_preview=not args.no_write_preview,
    )
    print(f"rows_xg={result.rows_xg}")
    print(f"rows_target={result.rows_target}")
    print(f"matched_rows={result.matched_rows}")
    print(f"join_coverage_pct={result.join_coverage_pct}")
    print(f"join_quality_label={result.join_quality_label}")
    print(f"output_path={result.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
