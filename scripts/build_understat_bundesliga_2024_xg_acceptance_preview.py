# -*- coding: utf-8 -*-
"""Build the reviewed Bundesliga 2024 Understat xG acceptance preview workflow."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from football_prediction_v19.importers.manual_xg_template_generator import generate_manual_xg_entry_template  # noqa: E402
from football_prediction_v19.importers.trusted_xg_manifest_promotion import run_trusted_xg_manifest_promotion  # noqa: E402
from football_prediction_v19.importers.trusted_xg_source import build_filled_manual_xg_preview  # noqa: E402
from football_prediction_v19.importers.understat_join_diagnostics import (  # noqa: E402
    build_understat_join_diagnostics,
    write_understat_join_diagnostics,
)
from football_prediction_v19.importers.manual_xg_acceptance import run_manual_xg_acceptance_gate  # noqa: E402
from apply_understat_team_alias_preview import apply_alias_preview  # noqa: E402
from apply_understat_date_alignment_preview import apply_date_alignment_preview  # noqa: E402
from audit_understat_team_alias_map import audit_alias_map, run as run_alias_audit  # noqa: E402
from audit_understat_date_alignment_map import audit_date_alignment_map, run as run_date_audit  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(ROOT / "data" / "trusted_xg_sources" / "understat_xg_bundesliga_2024.csv"))
    parser.add_argument("--alias-map", default=str(ROOT / "data" / "trusted_xg_sources" / "understat_team_alias_map_bundesliga_2024.csv"))
    parser.add_argument("--date-map", default=str(ROOT / "data" / "trusted_xg_sources" / "understat_date_alignment_bundesliga_2024.csv"))
    parser.add_argument("--target", default=str(ROOT / "data" / "processed" / "football_data_D1_2024_clean.csv"))
    parser.add_argument("--output-root", default=str(ROOT / "outputs"))
    return parser


def run_workflow(
    source: str | Path,
    alias_map: str | Path,
    date_map: str | Path,
    target: str | Path,
    output_root: str | Path = ROOT / "outputs",
) -> dict[str, object]:
    output_root = Path(output_root)
    diagnostics_dir = output_root / "diagnostics"
    diagnostics_dir.mkdir(parents=True, exist_ok=True)

    _alias_table, alias_rec, _alias_failures = audit_alias_map(alias_map)
    run_alias_audit(alias_map, diagnostics_dir)
    if alias_rec not in {"UNDERSTAT_TEAM_ALIAS_MAP_READY", "REVIEW_UNDERSTAT_TEAM_ALIAS_MAP"}:
        raise ValueError(f"Alias map is not ready for preview: {alias_rec}")
    _alias_df, alias_summary = apply_alias_preview(source, alias_map, output_root / "xg_alias_preview", overwrite=True)

    _date_table, date_rec, _date_failures = audit_date_alignment_map(date_map)
    run_date_audit(date_map, diagnostics_dir)
    if date_rec not in {"UNDERSTAT_DATE_ALIGNMENT_MAP_READY", "REVIEW_UNDERSTAT_DATE_ALIGNMENT_MAP"}:
        raise ValueError(f"Date alignment map is not ready for preview: {date_rec}")
    _date_df, date_summary = apply_date_alignment_preview(alias_summary["output_path"], date_map, output_root / "xg_date_alignment_preview", overwrite=True)

    join_result = build_understat_join_diagnostics(date_summary["output_path"], target)
    write_understat_join_diagnostics(join_result, diagnostics_dir)

    template_result = generate_manual_xg_entry_template(target, output_dir=output_root / "xg_entry_templates", write_template=True)
    _fill_preview, fill_summary = build_filled_manual_xg_preview(
        date_summary["output_path"],
        template_result.output_path,
        output_dir=output_root / "xg_fill_preview",
        write_preview=True,
    )
    acceptance = run_manual_xg_acceptance_gate(
        fill_summary["output_path"],
        target_path=target,
        output_dir=output_root / "xg_acceptance_preview",
        write_preview=True,
    )
    promotion = run_trusted_xg_manifest_promotion(
        date_summary["output_path"],
        target,
        target,
        output_dir=output_root / "xg_promotion_preview",
        write_manifest_preview=True,
    )
    return {
        "alias_recommendation": alias_rec,
        "date_alignment_recommendation": date_rec,
        "rows_date_aligned": date_summary["rows_date_aligned"],
        "unused_accepted_alignments": date_summary["unused_accepted_alignments"],
        "exact_matches": join_result.exact_matches,
        "missing_matches": join_result.missing_matches,
        "exact_coverage_pct": join_result.exact_coverage_pct,
        "join_recommendation": join_result.recommendation,
        "rows_filled": fill_summary["rows_filled"],
        "rows_missing_xg": fill_summary["rows_missing_xg"],
        "fill_preview_acceptance_label": acceptance.acceptance_label,
        "acceptance_label": promotion.acceptance_label,
        "promotion_label": promotion.promotion_label,
        "manifest_preview_path": promotion.manifest_preview_path,
        "aligned_source_path": date_summary["output_path"],
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_workflow(args.source, args.alias_map, args.date_map, args.target, args.output_root)
    for key in [
        "exact_matches",
        "rows_filled",
        "rows_missing_xg",
        "acceptance_label",
        "promotion_label",
        "manifest_preview_path",
    ]:
        print(f"{key}={summary[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
