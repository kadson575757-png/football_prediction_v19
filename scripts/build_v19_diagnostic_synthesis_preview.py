# -*- coding: utf-8 -*-
"""Build diagnostic-only v1.9 synthesis preview."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_context_bundle_human_input_bridge_preview import build_context_bundle_human_input_bridge_preview  # noqa: E402
from football_prediction_v19.analysis.v19_diagnostic_synthesis_preview import V19DiagnosticSynthesisConfig, V19DiagnosticSynthesisRunner  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context-human-input", default=None)
    parser.add_argument("--match-context-bundle", default=None)
    parser.add_argument("--cross-provider-match-key", default=None)
    parser.add_argument("--understat-provider-match-id", default=None)
    parser.add_argument("--fbref-provider-match-id", default=None)
    parser.add_argument("--home-team", default=None)
    parser.add_argument("--away-team", default=None)
    parser.add_argument("--match-date", default=None)
    parser.add_argument("--competition", default=None)
    parser.add_argument("--season", default=None)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis"))
    parser.add_argument("--base-dir", default=str(ROOT))
    parser.add_argument("--build-missing", action=argparse.BooleanOptionalAction, default=True)
    return parser


def build_v19_diagnostic_synthesis_preview(
    *,
    context_human_input_path: str | Path | None = None,
    match_context_bundle_path: str | Path | None = None,
    cross_provider_match_key: str | None = None,
    understat_provider_match_id: str | None = None,
    fbref_provider_match_id: str | None = None,
    home_team: str | None = None,
    away_team: str | None = None,
    match_date: str | None = None,
    competition: str | None = None,
    season: str | None = None,
    output_dir: str | Path = ROOT / "outputs" / "analysis_preview" / "v19_diagnostic_synthesis",
    base_dir: str | Path = ROOT,
    build_missing: bool = True,
) -> dict[str, object]:
    base = Path(base_dir).resolve()
    human_input = Path(context_human_input_path) if context_human_input_path else base / "outputs" / "analysis_preview" / "context_bundle_human_input" / "context_bundle_human_input.csv"
    if build_missing and not human_input.exists():
        bridge = build_context_bundle_human_input_bridge_preview(
            cross_provider_match_key=cross_provider_match_key or "u-bundesliga-2024-001",
            output_dir=base / "outputs" / "analysis_preview" / "context_bundle_human_input",
            base_dir=base,
        )
        human_input = Path(str(bridge.get("human_input_output_path", human_input)))
    result, _diagnostic = V19DiagnosticSynthesisRunner(V19DiagnosticSynthesisConfig(
        context_human_input_path=human_input,
        match_context_bundle_path=match_context_bundle_path,
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
    summary = build_v19_diagnostic_synthesis_preview(
        context_human_input_path=args.context_human_input,
        match_context_bundle_path=args.match_context_bundle,
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
        "v19_diagnostic_synthesis_status", "output_path", "summary_path", "rows_diagnosed",
        "candidates_checked", "candidates_matched", "missing_required_fields_count",
        "missing_optional_fields_count", "blocked_reasons_count", "v19_model_synthesis_status",
        "control_model_status", "chaos_score_status", "underdog_win_score_status",
        "no_bet_safety_status", "score_family_status", "dnb_gate_status",
        "over_under_gate_status", "away_favorite_degradation_status", "network_calls_enabled",
        "prediction_logic_enabled", "betting_logic_enabled", "staking_logic_enabled",
        "roi_logic_enabled", "recommendation",
    ]:
        value = summary.get(key, "")
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
