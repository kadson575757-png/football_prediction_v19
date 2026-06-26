# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT),str(ROOT/"src")]
from football_prediction_v19.analysis.v19_safety_invariant_scan_preview import run_safety_invariant_scan  # noqa: E402
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--output-dir", required=True); p.add_argument("--paths", nargs="*"); a=p.parse_args(argv)
    r=run_safety_invariant_scan(a.output_dir,a.paths); [print(f"{k}={str(v).lower() if isinstance(v,bool) else v}") for k,v in r.items()]; return 0
if __name__=="__main__": raise SystemExit(main())
