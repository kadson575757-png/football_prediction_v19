# -*- coding: utf-8 -*-
"""Build controlled Understat real snapshot smoke preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.importers.understat_real_snapshot_smoke_preview import UnderstatRealSnapshotSmokeConfig, UnderstatRealSnapshotSmokeRunner  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league", default="Bundesliga")
    parser.add_argument("--season", default="2024")
    parser.add_argument("--local-snapshot", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "provider_pull_preview" / "understat" / "real_snapshot"))
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--write-preview", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def build_understat_real_snapshot_smoke_preview(**kwargs) -> dict[str, object]:
    result, _frame = UnderstatRealSnapshotSmokeRunner(UnderstatRealSnapshotSmokeConfig(**kwargs)).run()
    return result.__dict__


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_understat_real_snapshot_smoke_preview(
        league=args.league,
        season=args.season,
        local_snapshot=args.local_snapshot,
        output_dir=args.output_dir,
        allow_network=args.allow_network,
        write_preview=args.write_preview,
        base_dir=args.base_dir,
    )
    for key in ["real_snapshot_status", "provider", "league", "season", "allow_network", "network_calls_enabled", "rows_raw", "rows_normalized", "rows_with_missing_required_values", "rows_with_missing_optional_values", "raw_snapshot_path", "normalized_output_path", "recommendation"]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
