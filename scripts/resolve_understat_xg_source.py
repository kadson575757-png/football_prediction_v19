# -*- coding: utf-8 -*-
"""Resolve a trusted Understat xG source through controlled fallback modes."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.understat_data_access import (  # noqa: E402
    MODES,
    resolve_understat_trusted_xg_source,
)
from football_prediction_v19.importers.understat_optional_provider import (  # noqa: E402
    check_understat_optional_provider,
    get_understat_optional_provider_install_command,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default=None)
    parser.add_argument("--season", default=None)
    parser.add_argument("--source", default=None)
    parser.add_argument("--output-name", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "data" / "trusted_xg_sources"))
    parser.add_argument("--raw-dir", default=str(ROOT / "data" / "trusted_xg_sources" / "raw"))
    parser.add_argument("--mode", action="append", choices=sorted(MODES), default=None)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--allow-optional-provider", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def _join(values: list[str]) -> str:
    return " | ".join(str(value) for value in values)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = resolve_understat_trusted_xg_source(
        league=args.league,
        season=args.season,
        source=args.source,
        output_name=args.output_name,
        output_dir=args.output_dir,
        raw_dir=args.raw_dir,
        modes=args.mode,
        overwrite=args.overwrite,
        allow_network=args.allow_network,
        allow_optional_provider=args.allow_optional_provider,
    )
    print(f"league={result.league}")
    print(f"season={result.season}")
    print(f"attempted_modes={_join(result.attempted_modes)}")
    print(f"successful_mode={result.successful_mode}")
    print(f"source_mode={result.source_mode}")
    print(f"source={result.source}")
    print(f"output_path={result.output_path}")
    print(f"rows_normalized={result.rows_normalized}")
    print(f"access_label={result.access_label}")
    if args.allow_optional_provider:
        provider = check_understat_optional_provider()
        print(f"optional_provider_available={provider.installed and provider.provider_label == 'UNDERSTAT_OPTIONAL_PROVIDER_AVAILABLE'}")
        if provider.provider_label != "UNDERSTAT_OPTIONAL_PROVIDER_AVAILABLE":
            print(f"install_command={get_understat_optional_provider_install_command()}")
            print("next_step_hint=Run scripts/bootstrap_understat_optional_provider.py --install, then retry with --allow-optional-provider.")
    elif result.access_label != "UNDERSTAT_ACCESS_READY":
        print("next_step_hint=Use --allow-optional-provider to try the optional soccerdata provider, or provide a local Understat export.")
    print(f"validation_errors={_join(result.validation_errors)}")
    print(f"warning_notes={_join(result.warning_notes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
