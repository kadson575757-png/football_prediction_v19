# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT), str(ROOT/"src")]
from football_prediction_v19.analysis.v20_final_release_gate import run_v20_final_release_gate
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--output-dir", required=True); p.add_argument("--emit-all", action="store_true"); p.add_argument("--repo-root", default=str(ROOT))
    a=p.parse_args(argv); r=run_v20_final_release_gate(a.output_dir, a.repo_root)
    for k in ["v20_final_release_gate_status","real_match_autopilot_status","real_source_smoke_status","no_leakage_backtest_status","one_command_runner_status","safety_scan_status","output_hygiene_status","docs_consistency_status","automatic_betting_enabled","staking_logic_enabled","roi_logic_enabled","recommendation"]:
        print(f"{k}={str(r.get(k)).lower() if isinstance(r.get(k), bool) else r.get(k)}")
    return 0
if __name__=="__main__": raise SystemExit(main())
