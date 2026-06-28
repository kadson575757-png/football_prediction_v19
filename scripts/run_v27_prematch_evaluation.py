# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v27_prematch_evaluation import run_prematch_evaluation  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="config/v27_real_prematch_eval_sample.csv")
    parser.add_argument("--source-profile", default="config/v20_internet_sources.yaml")
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument("--enable-network", action="store_true")
    parser.add_argument("--output-dir", default="outputs/v27_prematch_evaluation")
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)
    result = run_prematch_evaluation(
        input_csv=args.input,
        source_profile=args.source_profile,
        cache_only=args.cache_only,
        enable_network=args.enable_network,
        output_dir=args.output_dir,
    )
    for key in [
        "v27_prematch_evaluation_status",
        "matches_requested",
        "matches_evaluated",
        "result_known_count",
        "decision_count",
        "winner_pick_count",
        "winner_lean_count",
        "hit_count",
        "miss_count",
        "hit_rate",
        "no_decision_count",
        "no_decision_rate",
        "data_blocked_count",
        "data_blocked_rate",
        "result_unknown_count",
        "result_unknown_rate",
        "automatic_betting_enabled",
        "staking_logic_enabled",
        "roi_logic_enabled",
    ]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
