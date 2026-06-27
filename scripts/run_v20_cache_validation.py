# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from football_prediction_v19.analysis.v20_cache_validation_suite import run_cache_validation_suite

def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--cache-dir", required=True); p.add_argument("--output-dir", required=True); p.add_argument("--emit-all", action="store_true")
    a=p.parse_args(argv); r=run_cache_validation_suite(a.cache_dir, a.output_dir)
    for k in ["v20_cache_validation_status","cache_used","network_calls_enabled","automatic_betting_enabled","staking_logic_enabled","roi_logic_enabled"]:
        print(f"{k}={str(r[k]).lower() if isinstance(r[k], bool) else r[k]}")
    return 0
if __name__=="__main__": raise SystemExit(main())
