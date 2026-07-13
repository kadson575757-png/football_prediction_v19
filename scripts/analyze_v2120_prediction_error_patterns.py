# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v2120_prediction_error_patterns import analyze_prediction_error_patterns  # noqa: E402

DEFAULT_QUALITY_ROWS = "outputs/premier_league_2025_26_analysis_quality/pl_2025_26_analysis_quality_rows.csv"
DEFAULT_ANALYSIS_ROWS = "outputs/premier_league_2025_26_full_analysis/pl_2025_26_analysis_rows.csv"
DEFAULT_OUTPUT_DIR = "outputs/v2120_prediction_error_patterns"


def analyze_v2120_prediction_error_patterns(
    *,
    quality_rows: str | Path = DEFAULT_QUALITY_ROWS,
    analysis_rows: str | Path = DEFAULT_ANALYSIS_ROWS,
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
    return analyze_prediction_error_patterns(rows, output_dir=output_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze v2.12.0 main-model prediction error patterns.")
    parser.add_argument("--quality-rows", default=DEFAULT_QUALITY_ROWS)
    parser.add_argument("--analysis-rows", default=DEFAULT_ANALYSIS_ROWS)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--emit-all", action="store_true", help="Emit all diagnostic artifacts (currently always enabled).")
    args = parser.parse_args(argv)
    result = analyze_v2120_prediction_error_patterns(
        quality_rows=args.quality_rows,
        analysis_rows=args.analysis_rows,
        output_dir=args.output_dir,
    )
    keys = [
        "v2120_prediction_error_patterns_status", "rows_loaded", "evaluable_count",
        "baseline_hit_rate", "home_top_hit_rate", "draw_top_hit_rate", "away_top_hit_rate",
        "biggest_error_type", "biggest_error_type_count", "worst_edge_bucket",
        "worst_edge_bucket_hit_rate", "best_edge_bucket", "best_edge_bucket_hit_rate",
        "worst_top_probability_bucket", "worst_top_probability_bucket_hit_rate",
        "most_overpredicted_team_home", "most_overpredicted_team_away",
        "wrong_high_confidence_count", "correct_low_confidence_count", "main_error_problem",
        "recommendation", "output_dir", "automatic_betting_enabled", "staking_logic_enabled",
        "roi_logic_enabled",
    ]
    for key in keys:
        value = result.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
