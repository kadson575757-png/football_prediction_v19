# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT),str(ROOT/"src")]
from football_prediction_v19.analysis.v19_output_hygiene_guard_preview import run_output_hygiene_guard  # noqa: E402
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--output-dir", required=True); p.add_argument("--repo-root", default=str(ROOT)); a=p.parse_args(argv)
    r=run_output_hygiene_guard(a.output_dir, repo_root=a.repo_root); [print(f"{k}={str(v).lower() if isinstance(v,bool) else v}") for k,v in r.items()]; return 0
if __name__=="__main__": raise SystemExit(main())
