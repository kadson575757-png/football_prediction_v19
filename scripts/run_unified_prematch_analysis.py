#!/usr/bin/env python
"""CLI for the v2.16.0 unified prematch runner."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from football_prediction_v19.prematch.input_schema import load_batch_file, load_input_json, parse_match_input
from football_prediction_v19.prematch.unified_runner import DEFAULT_OUTPUT_DIR, analyze_match, run_batch


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the v2.16.0 unified, leakage-safe prematch analysis.")
    parser.add_argument("--competition")
    parser.add_argument("--season")
    parser.add_argument("--home-team")
    parser.add_argument("--away-team")
    parser.add_argument("--match-date")
    parser.add_argument("--project-root", default=str(ROOT))
    parser.add_argument("--output-dir")
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--input-json", help="Single match JSON file.")
    inputs.add_argument("--input-file", help="Batch CSV or JSONL file.")
    parser.add_argument("--emit-json", action="store_true", help="Print the complete JSON result.")
    parser.add_argument("--emit-markdown", action="store_true", help="Print the generated Markdown report.")
    parser.add_argument("--enable-network", action="store_true", help="Permit future optional network adapters (unused in v2.16.0).")
    parser.add_argument("--strict-asof", action="store_true", help="Fail on any as-of violation.")
    parser.add_argument("--max-scoreline-goals", type=int, default=10)
    parser.add_argument("--include-shadow-challenger", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project = Path(args.project_root).resolve()
    output = Path(args.output_dir) if args.output_dir else project / DEFAULT_OUTPUT_DIR
    if args.input_file:
        result = run_batch(
            load_batch_file(args.input_file),
            project_root=project,
            output_base=output,
            enable_network=args.enable_network,
            strict_asof=args.strict_asof,
            max_scoreline_goals=args.max_scoreline_goals,
            include_shadow_challenger=args.include_shadow_challenger,
        )
        print("unified_batch_analysis_status=" + result["status"])
        print("rows_loaded=" + str(result["successful_count"] + result["failed_count"]))
        print("rows_completed=" + str(result["successful_count"]))
        print("rows_failed=" + str(result["failed_count"]))
        print("probability_output_rate=" + str(result["successful_count"] / max(1, result["successful_count"] + result["failed_count"])))
        print("post_match_rows_used_count=" + str(sum(p["asof_audit"]["post_match_rows_used_count"] for p in result["predictions"])))
    else:
        match = load_input_json(args.input_json) if args.input_json else parse_match_input({
            "competition": args.competition,
            "season": args.season,
            "home_team": args.home_team,
            "away_team": args.away_team,
            "match_date": args.match_date,
        })
        result = analyze_match(
            match,
            project_root=project,
            output_base=output,
            enable_network=args.enable_network,
            strict_asof=args.strict_asof,
            max_scoreline_goals=args.max_scoreline_goals,
            include_shadow_challenger=args.include_shadow_challenger,
        )
        primary = result["winner_prediction"]
        print("unified_prematch_analysis_status=READY")
        print("competition=" + result["match"]["competition"])
        print("season=" + result["match"]["season"])
        print("match_date=" + result["match"]["match_date"])
        print("home_team=" + result["match"]["home_team"])
        print("away_team=" + result["match"]["away_team"])
        print("primary_winner_model=" + primary["model_name"])
        print("goal_distribution_model=" + result["goal_prediction"]["model_name"])
        print("home_probability=" + f"{primary['home_probability']:.6f}")
        print("draw_probability=" + f"{primary['draw_probability']:.6f}")
        print("away_probability=" + f"{primary['away_probability']:.6f}")
        print("top_outcome=" + primary["top_outcome"])
        print("expected_home_goals=" + f"{result['goal_prediction']['expected_home_goals']:.2f}")
        print("expected_away_goals=" + f"{result['goal_prediction']['expected_away_goals']:.2f}")
        print("expected_total_goals=" + f"{result['goal_prediction']['expected_total_goals']:.2f}")
        print("btts_yes_probability=" + f"{result['btts_prediction']['yes_probability']:.6f}")
        print("over_2_5_probability=" + f"{result['totals_prediction']['over_2_5_probability']:.6f}")
        print("top_scoreline=" + result["scoreline_prediction"]["top_1"]["score"])
        print("model_agreement=" + str(result["model_comparison"]["top_outcome_agreement"]).lower())
        print("conflict_level=" + result["model_comparison"]["conflict_level"])
        print("data_quality_grade=" + result["data_quality"]["quality_grade"])
        print("post_match_rows_used_count=" + str(result["asof_audit"]["post_match_rows_used_count"]))
        if args.include_shadow_challenger:
            shadow = result["shadow_winner_prediction"]
            comparison = result["shadow_comparison"]
            print("shadow_challenger_enabled=true")
            print("shadow_challenger_model=" + shadow["model_name"])
            print("shadow_home_probability=" + f"{shadow['home_probability']:.6f}")
            print("shadow_draw_probability=" + f"{shadow['draw_probability']:.6f}")
            print("shadow_away_probability=" + f"{shadow['away_probability']:.6f}")
            print("shadow_top_outcome=" + shadow["top_outcome"])
            print("shadow_primary_agreement=" + str(comparison["top_outcome_agreement"]).lower())
            print("shadow_probability_difference=" + f"{comparison['maximum_probability_difference']:.6f}")
            print("shadow_authoritative=false")
            print("probability_blending_applied=false")
        if args.emit_json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        if args.emit_markdown:
            print((Path(result["output_dir"]) / "report.md").read_text(encoding="utf-8"))
    if not args.include_shadow_challenger:
        print("shadow_challenger_enabled=false")
    print("output_dir=" + result["output_dir"])
    print("automatic_betting_enabled=false")
    print("staking_logic_enabled=false")
    print("roi_logic_enabled=false")
    print("productive_betting_enabled=false")
    return 0 if result.get("status", "READY") == "READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
