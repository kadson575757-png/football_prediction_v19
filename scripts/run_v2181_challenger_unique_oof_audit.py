#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from football_prediction_v19.analysis.v2181_challenger_unique_oof_audit import run_unique_oof_audit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the v2.18.1 unique-OOF challenger audit.")
    parser.add_argument("--project-root", default=str(ROOT))
    parser.add_argument("--input-dir")
    parser.add_argument("--output-dir")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_unique_oof_audit(
        args.project_root, input_dir=args.input_dir, output_dir=args.output_dir,
    )
    keys = [
        "v2181_challenger_unique_oof_audit_status", "raw_holdout_prediction_count",
        "unique_fixture_count", "duplicate_fixture_prediction_count",
        "maximum_predictions_per_fixture", "unique_oof_coverage_rate",
        "fold_baseline_hit_rate", "fold_challenger_hit_rate",
        "unique_baseline_hit_rate", "unique_challenger_hit_rate", "unique_hit_rate_delta",
        "unique_baseline_brier", "unique_challenger_brier", "unique_brier_improvement",
        "unique_baseline_log_loss", "unique_challenger_log_loss", "unique_log_loss_improvement",
        "best_simplified_component_model", "full_meta_hit_rate", "simplified_model_hit_rate",
        "unique_newly_corrected", "unique_newly_broken", "unique_net_corrected",
        "unique_draw_precision", "unique_draw_recall", "unique_draw_f1",
        "positive_holdout_rate", "dominant_competition_share", "dominant_team_share",
        "oof_leakage_count", "post_match_rows_used_count", "shadow_gate_status", "recommendation",
        "output_dir",
    ]
    for key in keys:
        print(f"{key}={result[key]}")
    for key in ("automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled", "productive_betting_enabled"):
        print(f"{key}=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
