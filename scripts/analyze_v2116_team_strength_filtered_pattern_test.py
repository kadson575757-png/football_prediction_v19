# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v21_league_support import normalize_team_or_league  # noqa: E402
from football_prediction_v19.analysis.v2116_team_strength_filtered_pattern_test import analyze_team_strength_filtered_patterns  # noqa: E402
from scripts.analyze_v2112_exact_scoreline_pattern_test import _prepare_matches, load_fixture_results  # noqa: E402

DEFAULT_OUTPUT_DIR = "outputs/v2116_team_strength_filtered_pattern_test"


def analyze_v2116_team_strength_filtered_pattern_test(
    *,
    competition: str = "Premier League",
    season: str = "2025/26",
    source_profile: str = "config/v20_internet_sources.yaml",
    enable_network: bool = False,
    cache_only: bool = False,
    limit: int = 0,
    team: str = "",
    from_date: str = "",
    to_date: str = "",
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    home_strength_tolerance: float = 0.45,
    away_strength_tolerance: float = 0.45,
    gap_strength_tolerance: float = 0.55,
    min_strength_matches: int = 3,
) -> dict[str, object]:
    fixtures = load_fixture_results(competition, season, output_dir, source_profile=source_profile, enable_network=enable_network, cache_only=cache_only)
    fixtures = _prepare_matches(fixtures, competition, season)
    if team:
        team_norm = normalize_team_or_league(team)
        fixtures = fixtures[
            fixtures["home_team"].map(normalize_team_or_league).eq(team_norm)
            | fixtures["away_team"].map(normalize_team_or_league).eq(team_norm)
        ]
    if from_date:
        fixtures = fixtures[fixtures["match_date"] >= from_date]
    if to_date:
        fixtures = fixtures[fixtures["match_date"] <= to_date]
    if limit:
        fixtures = fixtures.head(limit)
    return analyze_team_strength_filtered_patterns(
        fixtures,
        competition=competition,
        season=season,
        output_dir=output_dir,
        home_strength_tolerance=home_strength_tolerance,
        away_strength_tolerance=away_strength_tolerance,
        gap_strength_tolerance=gap_strength_tolerance,
        min_strength_matches=min_strength_matches,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--competition", default="Premier League")
    parser.add_argument("--season", default="2025/26")
    parser.add_argument("--source-profile", default="config/v20_internet_sources.yaml")
    parser.add_argument("--enable-network", action="store_true")
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--team", default="")
    parser.add_argument("--from-date", default="")
    parser.add_argument("--to-date", default="")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--home-strength-tolerance", type=float, default=0.45)
    parser.add_argument("--away-strength-tolerance", type=float, default=0.45)
    parser.add_argument("--gap-strength-tolerance", type=float, default=0.55)
    parser.add_argument("--min-strength-matches", type=int, default=3)
    parser.add_argument("--emit-all", action="store_true")
    args = parser.parse_args(argv)
    result = analyze_v2116_team_strength_filtered_pattern_test(
        competition=args.competition,
        season=args.season,
        source_profile=args.source_profile,
        enable_network=args.enable_network,
        cache_only=args.cache_only,
        limit=args.limit,
        team=args.team,
        from_date=args.from_date,
        to_date=args.to_date,
        output_dir=args.output_dir,
        home_strength_tolerance=args.home_strength_tolerance,
        away_strength_tolerance=args.away_strength_tolerance,
        gap_strength_tolerance=args.gap_strength_tolerance,
        min_strength_matches=args.min_strength_matches,
    )
    keys = [
        "v2116_team_strength_filtered_pattern_test_status",
        "competition",
        "season",
        "fixtures_loaded",
        "fixtures_analyzed",
        "baseline_goal_bucket_hit_rate",
        "best_goal_bucket_strategy",
        "best_goal_bucket_evaluable_count",
        "best_goal_bucket_hit_rate",
        "best_goal_bucket_delta_vs_baseline",
        "baseline_result_hit_rate",
        "best_result_strategy",
        "best_result_evaluable_count",
        "best_result_hit_rate",
        "best_result_delta_vs_baseline",
        "best_strategy_reference_count",
        "best_strategy_goals_2_3_bias",
        "recommendation",
        "output_dir",
        "automatic_betting_enabled",
        "staking_logic_enabled",
        "roi_logic_enabled",
    ]
    for key in keys:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
