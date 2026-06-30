# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.run_match_winner_analysis import run_match_winner_analysis  # noqa: E402


PROBABILITY_OUTPUT_KEYS = [
    "probability_analysis_status",
    "probability_model_status",
    "competition",
    "season",
    "home_team",
    "away_team",
    "match_date",
    "top_probability_outcome",
    "probability_edge",
    "probability_edge_band",
    "uncertainty_level",
    "data_quality_band",
    "probability_explanation_status",
    "probability_summary",
    "data_quality_notes",
    "probability_input_signals",
    "home_win_probability",
    "draw_probability",
    "away_win_probability",
    "base_home_win_probability",
    "base_draw_probability",
    "base_away_probability",
    "base_probability_explanation",
    "probability_explanation",
    "data_quality_explanation",
    "final_probability_explanation",
    "signal_alignment_summary",
    "signal_conflict_summary",
    "ppg_shadow_explanation",
    "last5_shadow_explanation",
    "goal_difference_shadow_explanation",
    "goals_for_shadow_explanation",
    "goals_against_shadow_explanation",
    "ppg_adjusted_home_win_probability",
    "ppg_adjusted_draw_probability",
    "ppg_adjusted_away_probability",
    "last5_adjusted_home_win_probability",
    "last5_adjusted_draw_probability",
    "last5_adjusted_away_probability",
    "gd_adjusted_home_win_probability",
    "gd_adjusted_draw_probability",
    "gd_adjusted_away_probability",
    "gf_adjusted_home_win_probability",
    "gf_adjusted_draw_probability",
    "gf_adjusted_away_probability",
    "ga_adjusted_home_win_probability",
    "ga_adjusted_draw_probability",
    "ga_adjusted_away_probability",
    "source_quality_band",
    "xg_available",
    "odds_available",
    "automatic_betting_enabled",
    "staking_logic_enabled",
    "roi_logic_enabled",
]


def run_match_probability_analysis(**kwargs: object) -> dict[str, object]:
    output_dir = kwargs.get("output_dir") or ROOT / "outputs" / "probability_analysis"
    result = run_match_winner_analysis(**{**kwargs, "output_dir": output_dir})
    probability = {key: result.get(key) for key in PROBABILITY_OUTPUT_KEYS if key != "probability_analysis_status"}
    probability["probability_analysis_status"] = "READY"
    probability["automatic_betting_enabled"] = False
    probability["staking_logic_enabled"] = False
    probability["roi_logic_enabled"] = False
    return probability


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--competition", required=True)
    parser.add_argument("--season", required=True)
    parser.add_argument("--home", required=True)
    parser.add_argument("--away", required=True)
    parser.add_argument("--match-date", default="")
    parser.add_argument("--as-of-date", default="")
    parser.add_argument("--allow-post-match-analysis", action="store_true")
    parser.add_argument("--source-profile", default="config/v20_internet_sources.yaml")
    parser.add_argument("--cache-only", action="store_true")
    parser.add_argument("--enable-network", action="store_true")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--emit-all", action="store_true")
    result = run_match_probability_analysis(**vars(parser.parse_args(argv)))
    for key in PROBABILITY_OUTPUT_KEYS:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
