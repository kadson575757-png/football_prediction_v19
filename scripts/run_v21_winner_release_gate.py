# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from football_prediction_v19.analysis.v21_winner_release_gate import run_v21_winner_release_gate  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", default="outputs/analysis_preview/v21_winner_release_gate")
    p.add_argument("--emit-all", action="store_true")
    result = run_v21_winner_release_gate(p.parse_args(argv).output_dir)
    for key in ["v21_winner_release_gate_status", "league_support_status", "fixture_catalog_status", "winner_model_status", "winner_runner_status", "winner_backtest_status", "safety_status", "recommendation", "automatic_betting_enabled", "staking_logic_enabled", "roi_logic_enabled"]:
        value = result.get(key)
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
