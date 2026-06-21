# -*- coding: utf-8 -*-
"""Build controlled FBref provider pull preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.fbref_provider_pull_preview import FBrefProviderPullConfig, FBrefProviderPullPreviewRunner  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition", default="Bundesliga")
    parser.add_argument("--season", default="2024")
    parser.add_argument("--local-input", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "provider_pull_preview" / "fbref"))
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--write-preview", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def build_fbref_provider_pull_preview(
    *,
    competition: str = "Bundesliga",
    season: str = "2024",
    local_input: str | Path | None = None,
    output_dir: str | Path = ROOT / "outputs" / "provider_pull_preview" / "fbref",
    allow_network: bool = False,
    write_preview: bool = True,
    base_dir: str | Path = ROOT,
) -> dict[str, object]:
    result, _frame = FBrefProviderPullPreviewRunner(FBrefProviderPullConfig(competition=competition, season=season, local_input=local_input, output_dir=output_dir, allow_network=allow_network, write_preview=write_preview, base_dir=base_dir)).run()
    return result.__dict__


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_fbref_provider_pull_preview(competition=args.competition, season=args.season, local_input=args.local_input, output_dir=args.output_dir, allow_network=args.allow_network, write_preview=args.write_preview, base_dir=args.base_dir)
    for key in ["fbref_provider_pull_status", "provider", "competition", "season", "allow_network", "network_calls_enabled", "rows_raw", "rows_normalized", "rows_with_missing_required_values", "rows_with_missing_optional_values", "raw_output_path", "normalized_output_path", "recommendation"]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
