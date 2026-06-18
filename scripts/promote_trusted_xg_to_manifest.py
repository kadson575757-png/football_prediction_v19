# -*- coding: utf-8 -*-
"""Create a trusted xG promotion preview and optional manifest-entry preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.trusted_xg_manifest_promotion import run_trusted_xg_manifest_promotion  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-xg", required=True)
    parser.add_argument("--template-source", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "xg_promotion_preview"))
    parser.add_argument("--min-join-coverage", type=float, default=95.0)
    parser.add_argument("--no-write-manifest-preview", action="store_true")
    parser.add_argument("--manifest-xg-path", default=None)
    parser.add_argument("--league", default=None)
    parser.add_argument("--season", default=None)
    parser.add_argument("--source-name", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_trusted_xg_manifest_promotion(
        args.source_xg,
        args.template_source,
        args.target,
        output_dir=args.output_dir,
        min_join_coverage=args.min_join_coverage,
        write_manifest_preview=not args.no_write_manifest_preview,
        manifest_xg_path=args.manifest_xg_path,
        league=args.league,
        season=args.season,
        source_name=args.source_name,
    )
    print(f"rows_template={result.rows_template}")
    print(f"rows_filled={result.rows_filled}")
    print(f"rows_missing_xg={result.rows_missing_xg}")
    print(f"rows_valid={result.rows_valid}")
    print(f"rows_invalid={result.rows_invalid}")
    print(f"rows_join_matched={result.rows_join_matched}")
    print(f"join_coverage_pct={result.join_coverage_pct}")
    print(f"acceptance_label={result.acceptance_label}")
    print(f"promotion_label={result.promotion_label}")
    print(f"manifest_registration_status={result.manifest_registration_status}")
    print(f"filled_preview_path={result.filled_preview_path}")
    print(f"manifest_preview_path={result.manifest_preview_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
