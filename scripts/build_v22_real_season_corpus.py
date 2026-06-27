# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v22_real_season_corpus import build_real_season_corpus  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--competition", required=True)
    p.add_argument("--season", required=True)
    p.add_argument("--source-profile", default="config/v20_internet_sources.yaml")
    p.add_argument("--output-dir", default="")
    p.add_argument("--mock-data-dir", default="")
    p.add_argument("--cache-dir", default="")
    p.add_argument("--enable-network", action="store_true")
    p.add_argument("--cache-only", action="store_true")
    p.add_argument("--emit-all", action="store_true")
    args = p.parse_args(argv)
    output = args.output_dir or f"outputs/corpus/v22/{args.competition.replace(' ', '_')}/{args.season.replace('/', '-')}"
    result = build_real_season_corpus(args.competition, args.season, output, source_profile=args.source_profile, enable_network=args.enable_network, cache_only=args.cache_only, cache_dir=args.cache_dir or None, mock_data_dir=args.mock_data_dir or None)
    for key in ["v22_real_season_corpus_status", "matches_total", "completed_matches", "backtestable_matches", "football_data_status", "understat_status", "cache_used", "network_calls_enabled"]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
