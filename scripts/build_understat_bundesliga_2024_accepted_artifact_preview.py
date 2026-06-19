# -*- coding: utf-8 -*-
"""Build or materialize the accepted Bundesliga 2024 trusted xG artifact."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_understat_bundesliga_2024_manifest_preview import run_manifest_preview  # noqa: E402
from football_prediction_v19.importers.trusted_xg_manifest_promotion import run_trusted_xg_manifest_promotion  # noqa: E402
from materialize_accepted_trusted_xg_artifact import materialize_accepted_trusted_xg_artifact  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(ROOT / "data" / "trusted_xg_sources" / "understat_xg_bundesliga_2024.csv"))
    parser.add_argument("--alias-map", default=str(ROOT / "data" / "trusted_xg_sources" / "understat_team_alias_map_bundesliga_2024.csv"))
    parser.add_argument("--date-map", default=str(ROOT / "data" / "trusted_xg_sources" / "understat_date_alignment_bundesliga_2024.csv"))
    parser.add_argument("--target", default=str(ROOT / "data" / "processed" / "football_data_D1_2024_clean.csv"))
    parser.add_argument("--output-root", default=str(ROOT / "outputs"))
    parser.add_argument("--accepted-output", default="data/trusted_xg_sources/accepted/understat_bundesliga_2024_manual_xg.csv")
    parser.add_argument("--write", action="store_true")
    return parser


def run_accepted_artifact_preview(
    source: str | Path,
    alias_map: str | Path,
    date_map: str | Path,
    target: str | Path,
    output_root: str | Path,
    accepted_output: str | Path,
    *,
    write: bool = False,
) -> dict[str, object]:
    output_root = Path(output_root)
    summary = run_manifest_preview(source, alias_map, date_map, target, output_root, accepted_output)
    promotion = run_trusted_xg_manifest_promotion(
        summary["aligned_source_path"],
        target,
        target,
        output_dir=output_root / "xg_promotion_preview",
        write_manifest_preview=True,
        manifest_xg_path=accepted_output,
        league="Bundesliga",
        season="2024",
        source_name="Understat Bundesliga 2024",
    )
    materialization = materialize_accepted_trusted_xg_artifact(
        promotion.filled_preview_path,
        accepted_output,
        target,
        league="Bundesliga",
        season="2024",
        source_name="Understat Bundesliga 2024",
        write=write,
        output_dir=output_root / "diagnostics",
    )
    return {
        **summary,
        "acceptance_label": promotion.acceptance_label,
        "promotion_label": promotion.promotion_label,
        "manifest_registration_status": promotion.manifest_registration_status,
        "materialization_status": materialization["materialization_status"],
        "accepted_output_path": materialization["accepted_output_path"],
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_accepted_artifact_preview(
        args.source,
        args.alias_map,
        args.date_map,
        args.target,
        args.output_root,
        args.accepted_output,
        write=args.write,
    )
    for key in [
        "exact_matches",
        "rows_filled",
        "rows_missing_xg",
        "acceptance_label",
        "promotion_label",
        "manifest_registration_status",
        "materialization_status",
        "accepted_output_path",
    ]:
        print(f"{key}={summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
