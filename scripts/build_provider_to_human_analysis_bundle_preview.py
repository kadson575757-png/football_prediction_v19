# -*- coding: utf-8 -*-
"""Build provider-to-human match analysis bundle preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.analysis.provider_to_human_analysis_bundle_preview import (  # noqa: E402
    ProviderToHumanAnalysisBundleConfig,
    ProviderToHumanAnalysisBundleRunner,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", default="understat")
    parser.add_argument("--league", default="Bundesliga")
    parser.add_argument("--season", default="2024")
    parser.add_argument("--provider-match-id", default="u-bundesliga-2024-001")
    parser.add_argument("--home-team", default=None)
    parser.add_argument("--away-team", default=None)
    parser.add_argument("--match-date", default=None)
    parser.add_argument("--alias-registry", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "provider_to_human_bundle"))
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--write-preview", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--build-missing", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def build_provider_to_human_analysis_bundle_preview(**kwargs) -> dict[str, object]:
    result, _steps = ProviderToHumanAnalysisBundleRunner(ProviderToHumanAnalysisBundleConfig(**kwargs)).run()
    return result.__dict__


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_provider_to_human_analysis_bundle_preview(
        provider=args.provider,
        league=args.league,
        season=args.season,
        provider_match_id=args.provider_match_id,
        home_team=args.home_team,
        away_team=args.away_team,
        match_date=args.match_date,
        alias_registry=args.alias_registry,
        output_dir=args.output_dir,
        allow_network=args.allow_network,
        write_preview=args.write_preview,
        build_missing=args.build_missing,
        base_dir=args.base_dir,
    )
    for key in [
        "bundle_status", "provider", "provider_match_id", "home_team", "away_team", "match_date",
        "provider_pull_status", "match_finder_status", "manual_input_bridge_status",
        "validation_status", "human_match_pipeline_status", "rows_reported", "steps_failed",
        "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled",
        "final_report_path", "recommendation",
    ]:
        value = summary.get(key, "")
        label = "provider_to_human_bundle_status" if key == "bundle_status" else key
        print(f"{label}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
