# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v2119_draw_signal_shadow_probe import analyze_draw_signal_shadow_probe  # noqa: E402

DEFAULT_QUALITY_ROWS = "outputs/premier_league_2025_26_analysis_quality/pl_2025_26_analysis_quality_rows.csv"
DEFAULT_ANALYSIS_ROWS = "outputs/premier_league_2025_26_full_analysis/pl_2025_26_analysis_rows.csv"
DEFAULT_OUTPUT_DIR = "outputs/v2119_draw_signal_shadow_probe"


def analyze_v2119_draw_signal_shadow_probe(
    *,
    quality_rows: str | Path = DEFAULT_QUALITY_ROWS,
    analysis_rows: str | Path = DEFAULT_ANALYSIS_ROWS,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, object]:
    quality = Path(quality_rows)
    analysis = Path(analysis_rows)
    if quality.exists():
        rows = pd.read_csv(quality, keep_default_na=False)
    elif analysis.exists():
        rows = pd.read_csv(analysis, keep_default_na=False)
    else:
        rows = pd.DataFrame()
    return analyze_draw_signal_shadow_probe(rows, output_dir=output_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quality-rows", default=DEFAULT_QUALITY_ROWS)
    parser.add_argument("--analysis-rows", default=DEFAULT_ANALYSIS_ROWS)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)
    result = analyze_v2119_draw_signal_shadow_probe(quality_rows=args.quality_rows, analysis_rows=args.analysis_rows, output_dir=args.output_dir)
    keys = [
        "v2119_draw_signal_shadow_probe_status",
        "rows_loaded",
        "evaluable_count",
        "baseline_hit_rate",
        "best_strategy_name",
        "best_strategy_hit_rate",
        "best_strategy_delta_vs_baseline",
        "best_strategy_draw_prediction_count",
        "best_strategy_draw_precision",
        "best_strategy_draw_recall",
        "best_strategy_newly_captured_draw_count",
        "best_strategy_newly_created_false_draw_count",
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
