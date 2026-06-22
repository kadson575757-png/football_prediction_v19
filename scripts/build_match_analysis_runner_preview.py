# -*- coding: utf-8 -*-
"""Build user-facing match analysis runner preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.analysis.match_analysis_runner_preview import MatchAnalysisRunnerConfig, MatchAnalysisRunnerPreviewRunner  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ["provider-match-id", "understat-provider-match-id", "fbref-provider-match-id", "cross-provider-match-key", "home-team", "away-team", "match-date", "competition", "season", "alias-registry"]:
        parser.add_argument(f"--{arg}", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "match_analysis_runner"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def build_match_analysis_runner_preview(**kwargs: object) -> dict[str, object]:
    result = MatchAnalysisRunnerPreviewRunner(MatchAnalysisRunnerConfig(**kwargs)).run()
    return result.__dict__


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_match_analysis_runner_preview(
        provider_match_id=args.provider_match_id,
        understat_provider_match_id=args.understat_provider_match_id,
        fbref_provider_match_id=args.fbref_provider_match_id,
        cross_provider_match_key=args.cross_provider_match_key,
        home_team=args.home_team,
        away_team=args.away_team,
        match_date=args.match_date,
        competition=args.competition,
        season=args.season,
        alias_registry=args.alias_registry,
        output_dir=args.output_dir,
        base_dir=args.base_dir,
    )
    for key in ["match_analysis_runner_status", "match_context_bundle_status", "context_bridge_status", "human_24_block_report_status", "v19_diagnostic_synthesis_status", "v19_diagnostic_gate_matrix_status", "odds_market_movement_input_status", "market_movement_diagnostic_status", "market_evidence_status", "market_movement_timing_flag", "lineups_availability_input_status", "availability_diagnostic_status", "availability_evidence_status", "gates_evaluated", "gates_blocked", "gates_disabled", "blocked_gate_count", "understat_provider_match_id", "fbref_provider_match_id", "cross_provider_match_key", "home_team", "away_team", "match_date", "rows_joined", "rows_written", "rows_reported", "sections_rendered", "report_output_path", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled", "recommendation"]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
