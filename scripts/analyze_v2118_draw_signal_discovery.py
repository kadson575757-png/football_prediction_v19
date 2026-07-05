# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v2118_draw_signal_discovery import analyze_draw_signal_discovery  # noqa: E402

DEFAULT_ANALYSIS_ROWS = "outputs/premier_league_2025_26_full_analysis/pl_2025_26_analysis_rows.csv"
DEFAULT_QUALITY_ROWS = "outputs/premier_league_2025_26_analysis_quality/pl_2025_26_analysis_quality_rows.csv"
DEFAULT_OUTPUT_DIR = "outputs/v2118_draw_signal_discovery"


def analyze_v2118_draw_signal_discovery(
    *,
    analysis_rows: str | Path = DEFAULT_ANALYSIS_ROWS,
    quality_rows: str | Path = DEFAULT_QUALITY_ROWS,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, object]:
    quality_path = Path(quality_rows)
    analysis_path = Path(analysis_rows)
    if quality_path.exists():
        rows = pd.read_csv(quality_path, keep_default_na=False)
    elif analysis_path.exists():
        rows = pd.read_csv(analysis_path, keep_default_na=False)
    else:
        rows = pd.DataFrame()
    return analyze_draw_signal_discovery(rows, output_dir=output_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis-rows", default=DEFAULT_ANALYSIS_ROWS)
    parser.add_argument("--quality-rows", default=DEFAULT_QUALITY_ROWS)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)
    result = analyze_v2118_draw_signal_discovery(analysis_rows=args.analysis_rows, quality_rows=args.quality_rows, output_dir=args.output_dir)
    keys = [
        "v2118_draw_signal_discovery_status",
        "rows_loaded",
        "evaluable_count",
        "baseline_draw_rate",
        "actual_draw_count",
        "best_signal_name",
        "best_signal_group",
        "best_signal_count",
        "best_signal_draw_rate",
        "best_signal_lift_vs_baseline",
        "best_combo_name",
        "best_combo_count",
        "best_combo_draw_rate",
        "best_combo_lift_vs_baseline",
        "draw_signal_found",
        "recommendation",
        "output_dir",
        "automatic_betting_enabled",
        "staking_logic_enabled",
        "roi_logic_enabled",
    ]
    for key in keys:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
