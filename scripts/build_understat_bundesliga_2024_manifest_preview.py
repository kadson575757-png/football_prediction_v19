# -*- coding: utf-8 -*-
"""Build a hardened reviewed manifest-entry preview for Bundesliga 2024 xG."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_understat_bundesliga_2024_xg_acceptance_preview import run_workflow  # noqa: E402
from football_prediction_v19.importers.trusted_xg_manifest_promotion import run_trusted_xg_manifest_promotion  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(ROOT / "data" / "trusted_xg_sources" / "understat_xg_bundesliga_2024.csv"))
    parser.add_argument("--alias-map", default=str(ROOT / "data" / "trusted_xg_sources" / "understat_team_alias_map_bundesliga_2024.csv"))
    parser.add_argument("--date-map", default=str(ROOT / "data" / "trusted_xg_sources" / "understat_date_alignment_bundesliga_2024.csv"))
    parser.add_argument("--target", default=str(ROOT / "data" / "processed" / "football_data_D1_2024_clean.csv"))
    parser.add_argument("--output-root", default=str(ROOT / "outputs"))
    parser.add_argument("--manifest-xg-path", default="data/trusted_xg_sources/accepted/understat_bundesliga_2024_manual_xg.csv")
    return parser


def run_manifest_preview(
    source: str | Path,
    alias_map: str | Path,
    date_map: str | Path,
    target: str | Path,
    output_root: str | Path,
    manifest_xg_path: str | Path,
) -> dict[str, object]:
    summary = run_workflow(source, alias_map, date_map, target, output_root)
    promotion = run_trusted_xg_manifest_promotion(
        summary["aligned_source_path"],
        target,
        target,
        output_dir=Path(output_root) / "xg_promotion_preview",
        write_manifest_preview=True,
        manifest_xg_path=manifest_xg_path,
        league="Bundesliga",
        season="2024",
        source_name="Understat Bundesliga 2024",
    )
    return {
        **summary,
        "acceptance_label": promotion.acceptance_label,
        "promotion_label": promotion.promotion_label,
        "manifest_registration_status": promotion.manifest_registration_status,
        "manifest_preview_path": promotion.manifest_preview_path,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_manifest_preview(args.source, args.alias_map, args.date_map, args.target, args.output_root, args.manifest_xg_path)
    for key in [
        "exact_matches",
        "rows_filled",
        "rows_missing_xg",
        "acceptance_label",
        "promotion_label",
        "manifest_registration_status",
        "manifest_preview_path",
    ]:
        print(f"{key}={summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
