# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path[:0]=[str(ROOT),str(ROOT/"src")]
from football_prediction_v19.analysis.v19_final_acceptance_gate_preview import run_final_acceptance_gate  # noqa: E402
def _read(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--output-dir", required=True); p.add_argument("--safety-json", required=True); p.add_argument("--hygiene-json", required=True); p.add_argument("--cli-json", required=True); p.add_argument("--docs-json", required=True); p.add_argument("--smoke-json"); a=p.parse_args(argv)
    r=run_final_acceptance_gate(a.output_dir,_read(a.safety_json),_read(a.hygiene_json),_read(a.cli_json),_read(a.docs_json),_read(a.smoke_json) if a.smoke_json else None); [print(f"{k}={str(v).lower() if isinstance(v,bool) else v}") for k,v in r.items()]; return 0
if __name__=="__main__": raise SystemExit(main())
