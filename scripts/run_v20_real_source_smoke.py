# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from football_prediction_v19.analysis.v20_real_source_smoke_suite import run_real_source_smoke_suite

def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--output-dir", required=True); p.add_argument("--enable-network", action="store_true"); p.add_argument("--emit-all", action="store_true")
    a=p.parse_args(argv); r=run_real_source_smoke_suite(a.output_dir, enable_network=a.enable_network)
    for k in ["v20_real_source_smoke_status","football_data_status","understat_status","odds_api_status","network_calls_enabled","automatic_betting_enabled","staking_logic_enabled","roi_logic_enabled"]:
        print(f"{k}={str(r[k]).lower() if isinstance(r[k], bool) else r[k]}")
    return 0
if __name__=="__main__": raise SystemExit(main())
