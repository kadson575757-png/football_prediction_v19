# -*- coding: utf-8 -*-
"""CLI wrapper for Phase 29 tactical / set-piece / fatigue input preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.analysis.tactical_set_piece_fatigue_input_preview import (  # noqa: E402
    TacticalSetPieceFatigueInputConfig,
    TacticalSetPieceFatigueInputRunner,
)


def build_tactical_set_piece_fatigue_input_preview(**kwargs: object) -> dict[str, object]:
    result = TacticalSetPieceFatigueInputRunner(TacticalSetPieceFatigueInputConfig(**kwargs)).run()
    return {
        "tactical_set_piece_fatigue_input_status": result.tactical_set_piece_fatigue_input_status,
        "rows_written": result.rows_written,
        "candidates_matched": result.candidates_matched,
        "missing_tactical_fields_count": result.missing_tactical_fields_count,
        "output_path": result.output_path,
        "summary_path": result.summary_path,
        "manifest_path": result.manifest_path,
        "recommendation": result.recommendation,
        "network_calls_enabled": result.network_calls_enabled,
        "prediction_logic_enabled": result.prediction_logic_enabled,
        "betting_logic_enabled": result.betting_logic_enabled,
        "staking_logic_enabled": result.staking_logic_enabled,
        "roi_logic_enabled": result.roi_logic_enabled,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cross-provider-match-key")
    parser.add_argument("--understat-provider-match-id")
    parser.add_argument("--fbref-provider-match-id")
    parser.add_argument("--home-team")
    parser.add_argument("--away-team")
    parser.add_argument("--match-date")
    parser.add_argument("--competition")
    parser.add_argument("--season")
    parser.add_argument("--tactical-input-path")
    parser.add_argument("--output-dir", default="outputs/analysis_preview/tactical_set_piece_fatigue_input")
    args = parser.parse_args()
    summary = build_tactical_set_piece_fatigue_input_preview(
        cross_provider_match_key=args.cross_provider_match_key,
        understat_provider_match_id=args.understat_provider_match_id,
        fbref_provider_match_id=args.fbref_provider_match_id,
        home_team=args.home_team,
        away_team=args.away_team,
        match_date=args.match_date,
        competition=args.competition,
        season=args.season,
        tactical_input_path=args.tactical_input_path,
        output_dir=args.output_dir,
        base_dir=ROOT,
    )
    for key, value in summary.items():
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
