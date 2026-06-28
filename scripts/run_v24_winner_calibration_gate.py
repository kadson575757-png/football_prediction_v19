# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v24_winner_calibration_gate import run_v24_winner_calibration_gate  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs/analysis_preview/v24_winner_calibration_gate")
    parser.add_argument("--diagnostics-dir", default="")
    parser.add_argument("--min-calibration-matches-required", type=int, default=50)
    parser.add_argument("--allow-insufficient-corpus", action="store_true")
    parser.add_argument("--enable-network", action="store_true")
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)
    result = run_v24_winner_calibration_gate(args.output_dir, args.diagnostics_dir or None, min_calibration_matches_required=args.min_calibration_matches_required, allow_insufficient_corpus=args.allow_insufficient_corpus, enable_network=args.enable_network)
    for key in [
        "v24_winner_calibration_gate_status",
        "calibration_dataset_status",
        "no_decision_diagnostics_status",
        "probability_diagnostics_status",
        "threshold_simulation_status",
        "confidence_calibration_status",
        "decision_policy_config_status",
        "real_backtest_status",
        "multileague_calibration_status",
        "real_matches_requested",
        "real_matches_available",
        "real_matches_evaluated",
        "multileague_matches_requested",
        "multileague_matches_available",
        "multileague_matches_evaluated",
        "min_calibration_matches_required",
        "auto_corpus_build_status",
        "sufficient_calibration_sample",
        "insufficient_corpus_warning",
        "safety_status",
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
