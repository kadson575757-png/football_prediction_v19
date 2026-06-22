# -*- coding: utf-8 -*-
"""Build preview-only player impact / rolling form input."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.analysis.player_impact_rolling_form_input_preview import PlayerImpactRollingFormInputConfig, PlayerImpactRollingFormInputRunner  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ["cross-provider-match-key", "understat-provider-match-id", "fbref-provider-match-id", "home-team", "away-team", "match-date", "competition", "season"]:
        parser.add_argument(f"--{arg}", default=None)
    parser.add_argument("--player-form-input-path", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "player_impact_rolling_form_input"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def build_player_impact_rolling_form_input_preview(**kwargs: object) -> dict[str, object]:
    return PlayerImpactRollingFormInputRunner(PlayerImpactRollingFormInputConfig(**kwargs)).run().__dict__


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_player_impact_rolling_form_input_preview(
        cross_provider_match_key=args.cross_provider_match_key,
        understat_provider_match_id=args.understat_provider_match_id,
        fbref_provider_match_id=args.fbref_provider_match_id,
        home_team=args.home_team,
        away_team=args.away_team,
        match_date=args.match_date,
        competition=args.competition,
        season=args.season,
        player_form_input_path=args.player_form_input_path,
        output_dir=args.output_dir,
        base_dir=args.base_dir,
    )
    for key in ["player_impact_rolling_form_input_status", "rows_written", "candidates_matched", "missing_player_form_fields_count", "output_path", "summary_path", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled", "recommendation"]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
