# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v202_real_no_odds_quality_gate import run_v202_real_no_odds_quality_gate  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs/analysis_preview/v202_real_no_odds_quality_gate")
    parser.add_argument("--emit-all", action="store_true")
    result = run_v202_real_no_odds_quality_gate(parser.parse_args(argv).output_dir)
    for key in ["v202_real_no_odds_quality_gate_status", "date_normalization_status", "fixture_search_status", "fixture_resolution_status", "understat_parse_status", "xg_bridge_status", "source_quality_status", "no_odds_policy_status", "safety_status", "recommendation", "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
