# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v2102_probability_output_schema import PROBABILITY_RUNNER_OUTPUT_FIELDS  # noqa: E402
from scripts.run_match_winner_analysis import run_match_winner_analysis  # noqa: E402


PROBABILITY_OUTPUT_KEYS = PROBABILITY_RUNNER_OUTPUT_FIELDS


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
