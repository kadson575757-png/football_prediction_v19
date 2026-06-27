# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT), str(ROOT/"src")]
from football_prediction_v19.analysis.v20_model_policy_calibrator import calibrate_v20_model_policy
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--output-dir", required=True); p.add_argument("--emit-all", action="store_true")
    a=p.parse_args(argv); r=calibrate_v20_model_policy(a.output_dir)
    print(f"v20_model_policy_calibration_status={r['v20_model_policy_calibration_status']}")
    print("automatic_betting_enabled=false\nstaking_logic_enabled=false\nroi_logic_enabled=false")
    return 0
if __name__=="__main__": raise SystemExit(main())
