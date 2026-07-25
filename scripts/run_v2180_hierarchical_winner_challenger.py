#!/usr/bin/env python
"""Run the v2.18.0 hierarchical winner shadow challenger."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from football_prediction_v19.analysis.v2180_winner_validation import DEFAULT_OUTPUT_DIR, run_validation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run leakage-safe v2.18.0 hierarchical winner challenger validation.")
    parser.add_argument("--project-root", default=str(ROOT))
    parser.add_argument("--output-dir")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.project_root).resolve()
    output = Path(args.output_dir) if args.output_dir else root / DEFAULT_OUTPUT_DIR
    result = run_validation(root, output)
    ordered = [
        "v2180_hierarchical_winner_challenger_status", "rows_loaded", "rows_evaluated",
        "competitions_evaluated", "seasons_evaluated", "outer_holdout_count",
        "baseline_model_name", "best_rating_model", "best_hierarchical_model",
        "best_meta_model", "best_feature_groups", "baseline_hit_rate", "challenger_hit_rate",
        "hit_rate_delta", "baseline_brier_score", "challenger_brier_score", "brier_improvement",
        "baseline_log_loss", "challenger_log_loss", "log_loss_improvement",
        "baseline_draw_top_count", "challenger_draw_top_count", "baseline_draw_recall",
        "challenger_draw_precision", "challenger_draw_recall", "challenger_draw_f1",
        "newly_corrected_count", "newly_broken_count", "net_corrected_count",
        "positive_holdout_rate", "worst_holdout_hit_delta", "dominant_competition_share",
        "dominant_team_share", "probability_output_rate", "invalid_probability_count",
        "oof_leakage_count", "post_match_rows_used_count", "challenger_status", "recommendation",
    ]
    for key in ordered:
        print(f"{key}={result[key]}")
    print("output_dir=" + str(output))
    for key in ("automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled", "productive_betting_enabled"):
        print(f"{key}=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
