# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v2117_draw_bias_diagnostics import analyze_draw_bias  # noqa: E402

DEFAULT_QUALITY_ROWS = "outputs/premier_league_2025_26_analysis_quality/pl_2025_26_analysis_quality_rows.csv"
DEFAULT_ANALYSIS_ROWS = "outputs/premier_league_2025_26_full_analysis/pl_2025_26_analysis_rows.csv"
DEFAULT_OUTPUT_DIR = "outputs/v2117_draw_bias_diagnostics"


def analyze_v2117_draw_bias_diagnostics(
    *,
    quality_rows: str | Path = DEFAULT_QUALITY_ROWS,
    analysis_rows: str | Path = DEFAULT_ANALYSIS_ROWS,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    min_draw_probability: float = 0.28,
    near_draw_edge: float = 0.05,
) -> dict[str, object]:
    rows_path = Path(quality_rows)
    fallback = Path(analysis_rows)
    if rows_path.exists():
        rows = pd.read_csv(rows_path, keep_default_na=False)
    elif fallback.exists():
        rows = pd.read_csv(fallback, keep_default_na=False)
    else:
        rows = pd.DataFrame()
    return analyze_draw_bias(rows, output_dir=output_dir, min_draw_probability=min_draw_probability, near_draw_edge=near_draw_edge)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quality-rows", default=DEFAULT_QUALITY_ROWS)
    parser.add_argument("--analysis-rows", default=DEFAULT_ANALYSIS_ROWS)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--min-draw-probability", type=float, default=0.28)
    parser.add_argument("--near-draw-edge", type=float, default=0.05)
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)
    result = analyze_v2117_draw_bias_diagnostics(
        quality_rows=args.quality_rows,
        analysis_rows=args.analysis_rows,
        output_dir=args.output_dir,
        min_draw_probability=args.min_draw_probability,
        near_draw_edge=args.near_draw_edge,
    )
    keys = [
        "v2117_draw_bias_diagnostics_status",
        "rows_loaded",
        "evaluable_count",
        "baseline_top_probability_hit_rate",
        "actual_draw_count",
        "actual_draw_rate",
        "predicted_draw_top_count",
        "predicted_draw_top_rate",
        "draw_top_hit_rate",
        "missed_draw_count",
        "average_draw_probability_on_actual_draws",
        "average_draw_probability_on_non_draws",
        "actual_draw_probability_gap",
        "actual_draw_rank_1_rate",
        "actual_draw_rank_2_rate",
        "actual_draw_rank_3_rate",
        "near_draw_candidate_count",
        "near_draw_precision",
        "near_draw_recall",
        "best_draw_lift_rule",
        "best_draw_lift_rule_hypothetical_top_hit_rate",
        "best_draw_lift_rule_delta_vs_baseline",
        "main_draw_problem",
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
