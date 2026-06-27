# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v21_winner_backtest import run_v21_winner_backtest  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--matches", default="")
    p.add_argument("--competition", default="Demo League")
    p.add_argument("--season", default="2025/26")
    p.add_argument("--source-profile", default="config/v20_internet_sources.yaml")
    p.add_argument("--output-dir", default="outputs/analysis_preview/v21_winner_backtest")
    p.add_argument("--mock-data-dir", default="tests/fixtures/v20_live_source_adapters")
    p.add_argument("--max-matches", type=int, default=0)
    p.add_argument("--cache-only", action="store_true")
    p.add_argument("--emit-all", action="store_true")
    args = p.parse_args(argv)
    matches = args.matches or _default_matches(Path(args.output_dir), args.competition, args.season)
    result = run_v21_winner_backtest(matches, args.output_dir, max_matches=args.max_matches or None, mock_data_dir=args.mock_data_dir, source_profile=args.source_profile, cache_only=args.cache_only)
    for key in ["v21_winner_backtest_status", "matches_total", "matches_evaluated", "winner_pick_count", "winner_lean_count", "no_clear_winner_count", "no_decision_count", "data_blocked_count", "top1_accuracy", "brier_score_1x2", "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


def _default_matches(output_dir: Path, competition: str, season: str) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "default_backtest_matches.csv"
    path.write_text("home_team,away_team,competition,season,match_date,actual_result\nDemo Home,Demo Away,%s,%s,2026-02-15,H\n" % (competition, season), encoding="utf-8")
    return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
