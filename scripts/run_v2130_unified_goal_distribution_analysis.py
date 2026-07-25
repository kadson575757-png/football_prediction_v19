# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v2130_goal_distribution import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    analyze_unified_goal_distribution,
    load_local_goal_results,
)


def run_v2130_unified_goal_distribution_analysis(
    *, output_dir: str | Path = DEFAULT_OUTPUT_DIR, project_root: str | Path = ROOT,
) -> dict[str, object]:
    project = Path(project_root)
    matches = load_local_goal_results(project)
    winner_paths = [
        project / "outputs/v2124_pl_multi_season_robustness/v2124_combined_rows.csv",
        project / "outputs/v2126_external_league_edge_calibration/v2126_external_rows.csv",
    ]
    winner_frames = [pd.read_csv(path, keep_default_na=False) for path in winner_paths if path.exists()]
    winner_rows = pd.concat(winner_frames, ignore_index=True) if winner_frames else pd.DataFrame()
    return analyze_unified_goal_distribution(matches, existing_winner_rows=winner_rows, output_dir=output_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run offline v2.13.0 unified goal distribution analysis.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--project-root", default=str(ROOT))
    args = parser.parse_args(argv)
    result = run_v2130_unified_goal_distribution_analysis(
        output_dir=args.output_dir, project_root=args.project_root,
    )
    keys = [
        "v2130_unified_goal_distribution_status", "rows_loaded", "rows_evaluated",
        "competitions_evaluated", "seasons_evaluated", "probability_output_rate",
        "best_model_name", "home_goals_mae", "away_goals_mae", "total_goals_mae",
        "winner_top_hit_rate", "winner_brier_score", "draw_top_count", "draw_top_hit_rate",
        "btts_brier_score", "btts_f1", "over_2_5_brier_score", "goal_bucket_hit_rate",
        "exact_score_top1_hit_rate", "exact_score_top3_hit_rate", "exact_score_top5_hit_rate",
        "positive_holdout_rate", "post_match_rows_used_count", "successful_component_count",
        "goal_distribution_status", "recommendation", "output_dir",
        "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled",
    ]
    for key in keys:
        value = result.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
