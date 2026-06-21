# -*- coding: utf-8 -*-
"""Build preview-only Understat + FBref match context bundle."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_fbref_provider_pull_preview import build_fbref_provider_pull_preview  # noqa: E402
from build_understat_real_snapshot_smoke_preview import build_understat_real_snapshot_smoke_preview  # noqa: E402
from football_prediction_v19.analysis.match_context_bundle_preview import MatchContextBundleConfig, MatchContextBundleRunner  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--understat-normalized-input", default=None)
    parser.add_argument("--fbref-normalized-input", default=None)
    parser.add_argument("--provider-match-id", default=None)
    parser.add_argument("--understat-provider-match-id", default=None)
    parser.add_argument("--fbref-provider-match-id", default=None)
    parser.add_argument("--cross-provider-match-key", default=None)
    parser.add_argument("--home-team", default=None)
    parser.add_argument("--away-team", default=None)
    parser.add_argument("--match-date", default=None)
    parser.add_argument("--competition", default=None)
    parser.add_argument("--season", default=None)
    parser.add_argument("--alias-registry", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "match_context_bundle"))
    parser.add_argument("--base-dir", default=str(ROOT))
    parser.add_argument("--build-missing", action=argparse.BooleanOptionalAction, default=True)
    return parser


def build_match_context_bundle_preview(
    *,
    understat_normalized_input: str | Path | None = None,
    fbref_normalized_input: str | Path | None = None,
    provider_match_id: str | None = None,
    understat_provider_match_id: str | None = None,
    fbref_provider_match_id: str | None = None,
    cross_provider_match_key: str | None = None,
    home_team: str | None = None,
    away_team: str | None = None,
    match_date: str | None = None,
    competition: str | None = None,
    season: str | None = None,
    alias_registry: str | Path | None = None,
    output_dir: str | Path = ROOT / "outputs" / "analysis_preview" / "match_context_bundle",
    base_dir: str | Path = ROOT,
    build_missing: bool = True,
) -> dict[str, object]:
    base = Path(base_dir).resolve()
    understat_input = Path(understat_normalized_input) if understat_normalized_input else base / "outputs" / "provider_pull_preview" / "understat" / "real_snapshot" / "normalized" / "understat_real_snapshot_normalized.csv"
    fbref_input = Path(fbref_normalized_input) if fbref_normalized_input else base / "outputs" / "provider_pull_preview" / "fbref" / "normalized" / "fbref_provider_pull_normalized.csv"
    if build_missing and not understat_input.exists():
        fixture = ROOT / "tests" / "fixtures" / "understat" / "understat_bundesliga_2024_fixture.json"
        summary = build_understat_real_snapshot_smoke_preview(local_snapshot=fixture, output_dir=base / "outputs" / "provider_pull_preview" / "understat" / "real_snapshot", base_dir=base)
        understat_input = Path(str(summary.get("normalized_output_path", understat_input)))
    if build_missing and not fbref_input.exists():
        fixture = ROOT / "tests" / "fixtures" / "fbref" / "fbref_bundesliga_2024_fixture.json"
        summary = build_fbref_provider_pull_preview(local_input=fixture, output_dir=base / "outputs" / "provider_pull_preview" / "fbref", base_dir=base)
        fbref_input = Path(str(summary.get("normalized_output_path", fbref_input)))
    result, _bundle = MatchContextBundleRunner(MatchContextBundleConfig(
        understat_normalized_input=understat_input,
        fbref_normalized_input=fbref_input,
        provider_match_id=provider_match_id,
        understat_provider_match_id=understat_provider_match_id,
        fbref_provider_match_id=fbref_provider_match_id,
        cross_provider_match_key=cross_provider_match_key,
        home_team=home_team,
        away_team=away_team,
        match_date=match_date,
        competition=competition,
        season=season,
        alias_registry=alias_registry,
        output_dir=output_dir,
        base_dir=base,
    )).run()
    return result.__dict__


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_match_context_bundle_preview(
        understat_normalized_input=args.understat_normalized_input,
        fbref_normalized_input=args.fbref_normalized_input,
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
        build_missing=args.build_missing,
    )
    for key in ["context_bundle_status", "understat_provider_match_id", "fbref_provider_match_id", "cross_provider_match_key", "home_team", "away_team", "match_date", "rows_joined", "candidates_checked", "candidates_matched", "missing_required_fields_count", "missing_optional_fields_count", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "recommendation"]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
