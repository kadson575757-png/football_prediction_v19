# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v28_coverage_diagnostics import write_v28_coverage_report  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", default="outputs/v27_prematch_evaluation/v27_prematch_evaluation_rows.csv")
    parser.add_argument("--output-dir", default="outputs/v28_coverage")
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)
    result = write_v28_coverage_report(args.rows, args.output_dir)
    for key in [
        "v28_coverage_status",
        "matches_requested",
        "ready_count",
        "ready_rate",
        "data_blocked_count",
        "data_blocked_rate",
        "not_found_count",
        "recommendation",
        "automatic_betting_enabled",
        "staking_logic_enabled",
        "roi_logic_enabled",
    ]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
