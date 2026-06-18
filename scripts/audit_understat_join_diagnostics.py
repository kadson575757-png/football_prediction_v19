# -*- coding: utf-8 -*-
"""Audit exact Understat-to-football-data join coverage and candidates."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.understat_join_diagnostics import (  # noqa: E402
    build_understat_join_diagnostics,
    write_understat_join_diagnostics,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "diagnostics"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_understat_join_diagnostics(args.source, args.target)
    paths = write_understat_join_diagnostics(result, args.output_dir)
    print(f"source_rows={result.source_rows}")
    print(f"target_rows={result.target_rows}")
    print(f"exact_matches={result.exact_matches}")
    print(f"missing_matches={result.missing_matches}")
    print(f"exact_coverage_pct={result.exact_coverage_pct}")
    print(f"same_date_candidate_matches={result.same_date_candidate_matches}")
    print(f"plus_minus_one_day_candidate_matches={result.plus_minus_one_day_candidate_matches}")
    print(f"diagnostic_label={result.diagnostic_label}")
    print(f"recommendation={result.recommendation}")
    print(f"summary_path={paths['summary_md']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
