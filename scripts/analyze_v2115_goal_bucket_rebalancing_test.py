# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v2115_goal_bucket_rebalancing_test import (  # noqa: E402
    run_goal_bucket_rebalancing,
    write_rebalancing_outputs,
)


DEFAULT_ROWS = "outputs/v2113_exact_scoreline_pattern_goal_bucket_test/v2113_exact_scoreline_goal_bucket_rows.csv"
DEFAULT_OUTPUT_DIR = "outputs/v2115_goal_bucket_rebalancing_test"


def analyze_goal_bucket_rebalancing(rows: str | Path | pd.DataFrame = DEFAULT_ROWS, output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, object]:
    frame = rows.copy() if isinstance(rows, pd.DataFrame) else pd.read_csv(rows, keep_default_na=False)
    strategy_rows, strategy_summary, summary = run_goal_bucket_rebalancing(frame)
    paths = write_rebalancing_outputs(strategy_rows, strategy_summary, summary, output_dir)
    return {**summary, **paths, "output_dir": str(output_dir)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", default=DEFAULT_ROWS)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)
    result = analyze_goal_bucket_rebalancing(args.rows, args.output_dir)
    for key in [
        "v2115_goal_bucket_rebalancing_test_status",
        "rows_loaded",
        "baseline_evaluable_count",
        "baseline_hit_rate",
        "best_strategy_name",
        "best_strategy_evaluable_count",
        "best_strategy_hit_rate",
        "best_strategy_delta_vs_baseline",
        "best_strategy_goals_0_1_precision",
        "best_strategy_goals_0_1_recall",
        "best_strategy_goals_2_3_precision",
        "best_strategy_goals_2_3_recall",
        "best_strategy_goals_4_plus_precision",
        "best_strategy_goals_4_plus_recall",
        "best_strategy_goals_2_3_prediction_bias",
        "recommendation",
        "output_dir",
        "automatic_betting_enabled",
        "staking_logic_enabled",
        "roi_logic_enabled",
    ]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
