# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from football_prediction_v19.analysis.v19_release_stabilization_preview import run_release_stabilization  # noqa: E402
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--output-dir", default=str(ROOT/"outputs/analysis_preview/v19_release_stabilization")); p.add_argument("--emit-all", action="store_true"); p.add_argument("--repo-root", default=str(ROOT)); a=p.parse_args(argv)
    r=run_release_stabilization(a.output_dir, emit_all=a.emit_all, repo_root=a.repo_root)
    [print(f"{k}={str(v).lower() if isinstance(v,bool) else v}") for k,v in r.items()]
    return 0
if __name__=="__main__": raise SystemExit(main())
