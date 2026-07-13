# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v2125_cross_season_edge_reliability import analyze_cross_season_edge_reliability  # noqa: E402

DEFAULT_INPUT = "outputs/v2124_pl_multi_season_robustness/v2124_combined_rows.csv"
DEFAULT_OUTPUT_DIR = "outputs/v2125_cross_season_edge_reliability"


def analyze_v2125_cross_season_edge_reliability(
    *,
    input_rows: str | Path = DEFAULT_INPUT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, object]:
    path = Path(input_rows)
    rows = pd.read_csv(path, keep_default_na=False) if path.exists() else pd.DataFrame()
    return analyze_cross_season_edge_reliability(rows, output_dir=output_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run v2.12.5 cross-season edge reliability holdouts.")
    parser.add_argument("--input-rows", default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--emit-all", action="store_true", help="Emit all diagnostic artifacts (currently always enabled).")
    args = parser.parse_args(argv)
    result = analyze_v2125_cross_season_edge_reliability(input_rows=args.input_rows, output_dir=args.output_dir)
    keys = [
        "v2125_cross_season_edge_reliability_status", "rows_loaded", "seasons_evaluated",
        "holdout_fold_count", "baseline_combined_hit_rate", "baseline_combined_brier_score",
        "most_selected_configuration", "same_configuration_selected_count",
        "positive_brier_holdout_count", "positive_hit_rate_holdout_count",
        "mean_holdout_brier_improvement", "mean_holdout_hit_rate_delta",
        "total_newly_corrected_count", "total_newly_broken_count", "total_net_corrected_count",
        "stable_edge_band_count", "best_stable_edge_band", "edge_calibration_status",
        "recommendation", "output_dir", "automatic_betting_enabled", "staking_logic_enabled",
        "roi_logic_enabled",
    ]
    for key in keys:
        value = result.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
