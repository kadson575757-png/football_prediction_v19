# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v28_supported_sample_builder import build_supported_evaluation_sample  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default="2025/26")
    parser.add_argument("--target-matches", type=int, default=40)
    parser.add_argument("--competitions", default="Premier League,Bundesliga,La Liga,Serie A,Ligue 1")
    parser.add_argument("--source-profile", default="config/v20_internet_sources.yaml")
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument("--enable-network", action="store_true")
    parser.add_argument("--output", default="config/v28_source_supported_eval_sample.csv")
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)
    result = build_supported_evaluation_sample(
        competitions=args.competitions,
        season=args.season,
        target_matches=args.target_matches,
        source_profile=args.source_profile,
        cache_only=args.cache_only,
        enable_network=args.enable_network,
        output_csv=args.output,
    )
    for key in [
        "v28_sample_builder_status",
        "requested_target_matches",
        "matches_written",
        "competitions_used",
        "source_used",
        "automatic_betting_enabled",
        "staking_logic_enabled",
        "roi_logic_enabled",
    ]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
