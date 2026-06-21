# -*- coding: utf-8 -*-
"""Find a deterministic FBref preview match from normalized provider output."""
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
from football_prediction_v19.importers.fbref_match_finder_preview import FBrefMatchFinderConfig, FBrefMatchFinderPreviewRunner  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normalized-input", default=None)
    parser.add_argument("--provider-match-id", default=None)
    parser.add_argument("--understat-provider-match-id", default=None)
    parser.add_argument("--home-team", default=None)
    parser.add_argument("--away-team", default=None)
    parser.add_argument("--match-date", default=None)
    parser.add_argument("--competition", default=None)
    parser.add_argument("--season", default=None)
    parser.add_argument("--alias-registry", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "provider_pull_preview" / "fbref" / "match_finder"))
    parser.add_argument("--base-dir", default=str(ROOT))
    parser.add_argument("--build-missing", action=argparse.BooleanOptionalAction, default=True)
    return parser


def find_fbref_match_preview(
    *,
    normalized_input: str | Path | None = None,
    provider_match_id: str | None = None,
    understat_provider_match_id: str | None = None,
    home_team: str | None = None,
    away_team: str | None = None,
    match_date: str | None = None,
    competition: str | None = None,
    season: str | None = None,
    alias_registry: str | Path | None = None,
    output_dir: str | Path = ROOT / "outputs" / "provider_pull_preview" / "fbref" / "match_finder",
    base_dir: str | Path = ROOT,
    build_missing: bool = True,
) -> dict[str, object]:
    normalized = Path(normalized_input) if normalized_input else Path(base_dir) / "outputs" / "provider_pull_preview" / "fbref" / "normalized" / "fbref_provider_pull_normalized.csv"
    if build_missing and not normalized.exists():
        summary = build_fbref_provider_pull_preview(base_dir=base_dir)
        normalized = Path(str(summary.get("normalized_output_path", normalized)))
    result, _selected = FBrefMatchFinderPreviewRunner(FBrefMatchFinderConfig(normalized_input=normalized, provider_match_id=provider_match_id, understat_provider_match_id=understat_provider_match_id, home_team=home_team, away_team=away_team, match_date=match_date, competition=competition, season=season, alias_registry=alias_registry, output_dir=output_dir, base_dir=base_dir)).run()
    return result.__dict__


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = find_fbref_match_preview(normalized_input=args.normalized_input, provider_match_id=args.provider_match_id, understat_provider_match_id=args.understat_provider_match_id, home_team=args.home_team, away_team=args.away_team, match_date=args.match_date, competition=args.competition, season=args.season, alias_registry=args.alias_registry, output_dir=args.output_dir, base_dir=args.base_dir, build_missing=args.build_missing)
    for key in ["fbref_match_finder_status", "provider", "provider_match_id", "cross_provider_match_key", "understat_provider_match_id", "home_team", "away_team", "match_date", "competition", "season", "candidates_checked", "candidates_matched", "alias_match_used", "network_calls_enabled", "prediction_logic_enabled", "betting_logic_enabled", "recommendation"]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
