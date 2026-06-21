# -*- coding: utf-8 -*-
"""Find exactly one match from normalized provider preview data."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_understat_provider_pull_preview_helper import run_workflow as build_understat_fixture  # noqa: E402
from football_prediction_v19.importers.provider_match_finder_preview import (  # noqa: E402
    ProviderMatchFinderConfig,
    ProviderMatchFinderPreview,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normalized-input", default=None)
    parser.add_argument("--provider-match-id", default=None)
    parser.add_argument("--home-team", default=None)
    parser.add_argument("--away-team", default=None)
    parser.add_argument("--match-date", default=None)
    parser.add_argument("--league", default=None)
    parser.add_argument("--season", default=None)
    parser.add_argument("--alias-registry", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "provider_pull_preview" / "match_finder"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def find_provider_match_preview(*, normalized_input: str | Path | None = None, provider_match_id: str | None = None, home_team: str | None = None, away_team: str | None = None, match_date: str | None = None, league: str | None = None, season: str | None = None, alias_registry: str | Path | None = None, output_dir: str | Path = ROOT / "outputs" / "provider_pull_preview" / "match_finder", base_dir: str | Path = ROOT, build_missing: bool = True) -> dict[str, object]:
    base = Path(base_dir).resolve()
    if normalized_input is None and build_missing and not _default_normalized(base).exists():
        build_understat_fixture(base / "outputs" / "provider_pull_preview" / "understat")
    result, _frame = ProviderMatchFinderPreview(
        ProviderMatchFinderConfig(
            normalized_input=normalized_input,
            provider_match_id=provider_match_id,
            home_team=home_team,
            away_team=away_team,
            match_date=match_date,
            league=league,
            season=season,
            alias_registry=alias_registry,
            output_dir=output_dir,
            base_dir=base,
        )
    ).find()
    return result.__dict__


def _default_normalized(base: Path) -> Path:
    normalized_dir = base / "outputs" / "provider_pull_preview" / "understat" / "normalized"
    matches = sorted(normalized_dir.glob("*_normalized_preview.csv"))
    return matches[0] if matches else normalized_dir / "understat_provider_pull_normalized.csv"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = find_provider_match_preview(
        normalized_input=args.normalized_input,
        provider_match_id=args.provider_match_id,
        home_team=args.home_team,
        away_team=args.away_team,
        match_date=args.match_date,
        league=args.league,
        season=args.season,
        alias_registry=args.alias_registry,
        output_dir=args.output_dir,
        base_dir=args.base_dir,
    )
    for key in ["match_finder_status", "provider", "provider_match_id", "home_team", "away_team", "match_date", "candidates_checked", "candidates_matched", "alias_match_used", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "recommendation"]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
