# -*- coding: utf-8 -*-
"""Build diagnostic-only v1.9 gate matrix preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_v19_diagnostic_synthesis_preview import build_v19_diagnostic_synthesis_preview  # noqa: E402
from football_prediction_v19.analysis.v19_diagnostic_gate_matrix_preview import V19DiagnosticGateMatrixConfig, V19DiagnosticGateMatrixRunner  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v19-diagnostic-synthesis", default=None)
    parser.add_argument("--context-human-input", default=None)
    parser.add_argument("--cross-provider-match-key", default=None)
    parser.add_argument("--understat-provider-match-id", default=None)
    parser.add_argument("--fbref-provider-match-id", default=None)
    parser.add_argument("--home-team", default=None)
    parser.add_argument("--away-team", default=None)
    parser.add_argument("--match-date", default=None)
    parser.add_argument("--competition", default=None)
    parser.add_argument("--season", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "v19_diagnostic_gate_matrix"))
    parser.add_argument("--base-dir", default=str(ROOT))
    parser.add_argument("--build-missing", action=argparse.BooleanOptionalAction, default=True)
    return parser


def build_v19_diagnostic_gate_matrix_preview(
    *,
    v19_diagnostic_synthesis_path: str | Path | None = None,
    context_human_input_path: str | Path | None = None,
    cross_provider_match_key: str | None = None,
    understat_provider_match_id: str | None = None,
    fbref_provider_match_id: str | None = None,
    home_team: str | None = None,
    away_team: str | None = None,
    match_date: str | None = None,
    competition: str | None = None,
    season: str | None = None,
    output_dir: str | Path = ROOT / "outputs" / "analysis_preview" / "v19_diagnostic_gate_matrix",
    base_dir: str | Path = ROOT,
    build_missing: bool = True,
) -> dict[str, object]:
    base = Path(base_dir).resolve()
    synthesis = Path(v19_diagnostic_synthesis_path) if v19_diagnostic_synthesis_path else base / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis" / "v19_diagnostic_synthesis.csv"
    if build_missing and not synthesis.exists():
        summary = build_v19_diagnostic_synthesis_preview(
            context_human_input_path=context_human_input_path,
            cross_provider_match_key=cross_provider_match_key or "u-bundesliga-2024-001",
            understat_provider_match_id=understat_provider_match_id,
            fbref_provider_match_id=fbref_provider_match_id,
            home_team=home_team,
            away_team=away_team,
            match_date=match_date,
            competition=competition,
            season=season,
            output_dir=base / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis",
            base_dir=base,
        )
        synthesis = Path(str(summary.get("output_path", synthesis)))
    result, _matrix = V19DiagnosticGateMatrixRunner(V19DiagnosticGateMatrixConfig(
        v19_diagnostic_synthesis_path=synthesis,
        context_human_input_path=context_human_input_path,
        cross_provider_match_key=cross_provider_match_key,
        understat_provider_match_id=understat_provider_match_id,
        fbref_provider_match_id=fbref_provider_match_id,
        home_team=home_team,
        away_team=away_team,
        match_date=match_date,
        competition=competition,
        season=season,
        output_dir=output_dir,
        base_dir=base,
    )).run()
    return result.__dict__


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_v19_diagnostic_gate_matrix_preview(
        v19_diagnostic_synthesis_path=args.v19_diagnostic_synthesis,
        context_human_input_path=args.context_human_input,
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
        build_missing=args.build_missing,
    )
    for key in [
        "v19_diagnostic_gate_matrix_status", "gate_matrix_output_path",
        "gates_evaluated", "gates_ready", "gates_blocked", "gates_disabled",
        "gates_missing_optional_data", "candidates_checked", "candidates_matched",
        "missing_required_fields_count", "missing_optional_fields_count",
        "blocked_gate_count", "network_calls_enabled", "prediction_logic_enabled",
        "betting_logic_enabled", "staking_logic_enabled", "roi_logic_enabled",
        "recommendation",
    ]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
