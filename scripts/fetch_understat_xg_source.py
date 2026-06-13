# -*- coding: utf-8 -*-
"""Fetch an explicit Understat league/season page into trusted xG sources."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.understat_fetch import fetch_understat_league_season  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=None)
    parser.add_argument("--season", default=None)
    parser.add_argument("--url", default=None)
    parser.add_argument("--output-name", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "data" / "trusted_xg_sources"))
    parser.add_argument("--raw-output-dir", default=str(ROOT / "data" / "trusted_xg_sources" / "raw"))
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--no-fetch", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = fetch_understat_league_season(
        league=args.league,
        season=args.season,
        url=args.url,
        output_name=args.output_name,
        output_dir=args.output_dir,
        raw_output_dir=args.raw_output_dir,
        overwrite=args.overwrite,
        no_fetch=args.no_fetch,
    )
    print(f"league={result.league}")
    print(f"season={result.season}")
    print(f"source_url={result.source_url}")
    print(f"raw_output_path={result.raw_output_path}")
    print(f"output_path={result.output_path}")
    print(f"matches_found={result.matches_found}")
    print(f"rows_normalized={result.rows_normalized}")
    print(f"fetch_label={result.fetch_label}")
    print(f"html_state={result.html_state}")
    print(f"fallback_endpoints_checked={result.fallback_endpoints_checked}")
    print(f"fallback_endpoint_used={result.fallback_endpoint_used}")
    print(f"validation_errors={' | '.join(result.validation_errors)}")
    print(f"warning_notes={' | '.join(result.warning_notes)}")
    if (
        result.fetch_label == "UNDERSTAT_FETCH_BLOCKED_PARSE_FAILED"
        and result.html_state == "UNDERSTAT_HTML_HAS_BASE_PAGE_ONLY"
    ):
        print(
            "next_step_hint=Try scripts/resolve_understat_xg_source.py --league Bundesliga "
            "--season 2024 --allow-optional-provider or provide --source local_export.csv."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
