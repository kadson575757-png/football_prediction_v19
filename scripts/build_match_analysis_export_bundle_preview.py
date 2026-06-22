# -*- coding: utf-8 -*-
"""Build preview-only match analysis export bundle."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.analysis.match_analysis_export_bundle_preview import MatchAnalysisExportBundleConfig, MatchAnalysisExportBundleRunner  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ["cross-provider-match-key", "understat-provider-match-id", "fbref-provider-match-id", "home-team", "away-team", "match-date", "competition", "season"]:
        parser.add_argument(f"--{arg}", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "match_analysis_export_bundle"))
    parser.add_argument("--base-dir", default=str(ROOT))
    return parser


def build_match_analysis_export_bundle_preview(**kwargs: object) -> dict[str, object]:
    result = MatchAnalysisExportBundleRunner(MatchAnalysisExportBundleConfig(**kwargs)).run()
    return result.__dict__


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_match_analysis_export_bundle_preview(
        cross_provider_match_key=args.cross_provider_match_key,
        understat_provider_match_id=args.understat_provider_match_id,
        fbref_provider_match_id=args.fbref_provider_match_id,
        home_team=args.home_team,
        away_team=args.away_team,
        match_date=args.match_date,
        competition=args.competition,
        season=args.season,
        output_dir=args.output_dir,
        base_dir=args.base_dir,
    )
    for key in [
        "export_bundle_status", "match_analysis_runner_status",
        "v19_diagnostic_synthesis_status", "v19_diagnostic_gate_matrix_status",
        "human_24_block_report_status", "exported_files_count", "sections_rendered",
        "required_sections_rendered", "gates_evaluated", "gates_blocked",
        "gates_disabled", "network_calls_enabled", "prediction_logic_enabled",
        "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled",
        "recommendation",
    ]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
