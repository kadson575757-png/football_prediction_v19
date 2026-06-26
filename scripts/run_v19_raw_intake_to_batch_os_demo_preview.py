# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from scripts.run_v19_final_pipeline_preview import run_v19_final_pipeline_preview  # noqa: E402
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--raw-input-dir", required=True); p.add_argument("--output-dir", required=True); p.add_argument("--emit-all", action="store_true"); p.add_argument("--base-dir", default=str(ROOT)); a=p.parse_args(argv)
    r=run_v19_final_pipeline_preview(raw_input_dir=a.raw_input_dir, output_dir=a.output_dir, emit_all=a.emit_all, base_dir=a.base_dir)
    [print(f"{k}={str(v).lower() if isinstance(v,bool) else v}") for k,v in r.items()]
    return 0
if __name__=="__main__": raise SystemExit(main())
