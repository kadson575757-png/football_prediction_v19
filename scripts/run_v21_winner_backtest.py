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
    p.add_argument("--corpus-path", default="")
    p.add_argument("--competition", default="Demo League")
    p.add_argument("--season", default="2025/26")
    p.add_argument("--source-profile", default="config/v20_internet_sources.yaml")
    p.add_argument("--output-dir", default="outputs/analysis_preview/v21_winner_backtest")
    p.add_argument("--mock-data-dir", default="")
    p.add_argument("--max-matches", type=int, default=0)
    p.add_argument("--min-matches-required", type=int, default=10)
    p.add_argument("--allow-small-sample", action="store_true")
    p.add_argument("--enable-network", action="store_true")
    p.add_argument("--cache-only", action="store_true")
    p.add_argument("--decision-policy-config", default="")
    p.add_argument("--emit-calibration-diagnostics", action="store_true")
    p.add_argument("--emit-threshold-simulation", action="store_true")
    p.add_argument("--emit-all", action="store_true")
    args = p.parse_args(argv)
    matches = args.matches or ""
    result = run_v21_winner_backtest(matches or None, args.output_dir, competition=args.competition, season=args.season, corpus_path=args.corpus_path or None, max_matches=args.max_matches or None, min_matches_required=args.min_matches_required, allow_small_sample=args.allow_small_sample, mock_data_dir=args.mock_data_dir, source_profile=args.source_profile, cache_only=args.cache_only, enable_network=args.enable_network, decision_policy_config=args.decision_policy_config or None, emit_calibration_diagnostics=args.emit_calibration_diagnostics, emit_threshold_simulation=args.emit_threshold_simulation)
    for key in ["v21_winner_backtest_status", "matches_requested", "matches_available", "matches_total", "matches_evaluated", "corpus_status", "corpus_path", "corpus_rows_loaded", "corpus_expected_min_rows", "recommendation", "statistical_validity", "fallback_data_used", "sample_warning", "calibration_diagnostics_status", "threshold_simulation_status", "active_decision_policy", "winner_pick_count", "winner_lean_count", "no_clear_winner_count", "no_decision_count", "decision_coverage_rate", "data_blocked_count", "hard_data_blocked_count", "invalid_data_blocked_count", "decision_attempt_count", "model_ran_count", "probabilities_created_count", "no_xg_partial_model_count", "odds_missing_non_block_count", "understat_failed_non_block_count", "average_top_edge", "median_top_edge", "confidence_cap_rate", "results_only_rate", "xg_missing_rate", "selected_policy_top1_accuracy_decisions_only", "selected_policy_brier_score_decisions_only", "top1_accuracy", "brier_score_1x2", "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
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
