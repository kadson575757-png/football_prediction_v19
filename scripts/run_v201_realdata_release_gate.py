# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v201_realdata_release_gate import run_v201_realdata_release_gate  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default="outputs/analysis_preview/v201_realdata_release_gate")
    p.add_argument("--emit-all", action="store_true")
    result = run_v201_realdata_release_gate(p.parse_args(argv).output_dir)
    for key in ["v201_realdata_release_gate_status", "football_data_status", "understat_status", "no_odds_policy_status", "fixture_search_status", "realdata_smoke_status", "cache_only_status", "backtest_without_odds_status", "safety_status", "recommendation", "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
