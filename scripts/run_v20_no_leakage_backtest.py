# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from football_prediction_v19.analysis.v20_no_leakage_backtest_runner import run_no_leakage_backtest

def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--matches", required=True); p.add_argument("--output-dir", required=True); p.add_argument("--source-profile", default="config/v20_internet_sources.yaml"); p.add_argument("--mock-data-dir", default=""); p.add_argument("--max-matches", type=int, default=0); p.add_argument("--emit-all", action="store_true")
    a=p.parse_args(argv); r=run_no_leakage_backtest(a.matches, a.output_dir, mock_data_dir=a.mock_data_dir, source_profile=a.source_profile, max_matches=a.max_matches or None)
    for k in ["v20_no_leakage_backtest_status","matches_total","matches_evaluated","model_tip_count","analyst_lean_count","no_bet_count","data_blocked_count","brier_score","accuracy_1x2","leakage_blocked_count","automatic_betting_enabled","staking_logic_enabled","roi_logic_enabled"]:
        print(f"{k}={str(r.get(k)).lower() if isinstance(r.get(k), bool) else r.get(k)}")
    return 0
if __name__=="__main__": raise SystemExit(main())
