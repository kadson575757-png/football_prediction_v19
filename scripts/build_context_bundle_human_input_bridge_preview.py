# -*- coding: utf-8 -*-
"""Build context bundle to human analysis input bridge preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_match_context_bundle_preview import build_match_context_bundle_preview  # noqa: E402
from football_prediction_v19.analysis.context_bundle_human_input_bridge_preview import ContextBundleHumanInputBridgeConfig, ContextBundleHumanInputBridgeRunner  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--match-context-bundle", default=None)
    parser.add_argument("--context-bundle-id", default=None)
    parser.add_argument("--understat-provider-match-id", default=None)
    parser.add_argument("--fbref-provider-match-id", default=None)
    parser.add_argument("--cross-provider-match-key", default=None)
    parser.add_argument("--home-team", default=None)
    parser.add_argument("--away-team", default=None)
    parser.add_argument("--match-date", default=None)
    parser.add_argument("--competition", default=None)
    parser.add_argument("--season", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "context_bundle_human_input"))
    parser.add_argument("--base-dir", default=str(ROOT))
    parser.add_argument("--build-missing", action=argparse.BooleanOptionalAction, default=True)
    return parser


def build_context_bundle_human_input_bridge_preview(
    *,
    match_context_bundle_path: str | Path | None = None,
    context_bundle_id: str | None = None,
    understat_provider_match_id: str | None = None,
    fbref_provider_match_id: str | None = None,
    cross_provider_match_key: str | None = None,
    home_team: str | None = None,
    away_team: str | None = None,
    match_date: str | None = None,
    competition: str | None = None,
    season: str | None = None,
    output_dir: str | Path = ROOT / "outputs" / "analysis_preview" / "context_bundle_human_input",
    base_dir: str | Path = ROOT,
    build_missing: bool = True,
) -> dict[str, object]:
    base = Path(base_dir).resolve()
    bundle_path = Path(match_context_bundle_path) if match_context_bundle_path else base / "outputs" / "analysis_preview" / "match_context_bundle" / "match_context_bundle.csv"
    if build_missing and not bundle_path.exists():
        summary = build_match_context_bundle_preview(cross_provider_match_key=cross_provider_match_key or "u-bundesliga-2024-001", output_dir=base / "outputs" / "analysis_preview" / "match_context_bundle", base_dir=base)
        bundle_path = Path(str(summary.get("output_path", bundle_path)))
    result, _human = ContextBundleHumanInputBridgeRunner(ContextBundleHumanInputBridgeConfig(
        match_context_bundle_path=bundle_path,
        context_bundle_id=context_bundle_id,
        understat_provider_match_id=understat_provider_match_id,
        fbref_provider_match_id=fbref_provider_match_id,
        cross_provider_match_key=cross_provider_match_key,
        home_team=home_team,
        away_team=away_team,
        match_date=match_date,
        competition=competition,
        season=season,
        output_dir=output_dir,
        base_dir=base,
    )).run()
    return result.__dict__


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_context_bundle_human_input_bridge_preview(
        match_context_bundle_path=args.match_context_bundle,
        context_bundle_id=args.context_bundle_id,
        understat_provider_match_id=args.understat_provider_match_id,
        fbref_provider_match_id=args.fbref_provider_match_id,
        cross_provider_match_key=args.cross_provider_match_key,
        home_team=args.home_team,
        away_team=args.away_team,
        match_date=args.match_date,
        competition=args.competition,
        season=args.season,
        output_dir=args.output_dir,
        base_dir=args.base_dir,
        build_missing=args.build_missing,
    )
    for key in ["context_bridge_status", "context_bundle_id", "understat_provider_match_id", "fbref_provider_match_id", "cross_provider_match_key", "home_team", "away_team", "match_date", "rows_written", "candidates_checked", "candidates_matched", "missing_required_fields_count", "missing_optional_fields_count", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "recommendation"]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
