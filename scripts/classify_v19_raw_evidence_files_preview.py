# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from football_prediction_v19.analysis.v19_raw_evidence_file_classifier_preview import classify_raw_evidence_files  # noqa: E402
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument("--raw-input-dir", required=True); p.add_argument("--output-dir", required=True); a=p.parse_args(argv)
    r=classify_raw_evidence_files(a.raw_input_dir,a.output_dir)
    [print(f"{k}={str(v).lower() if isinstance(v,bool) else v}") for k,v in r.items()]
    return 0
if __name__=="__main__": raise SystemExit(main())
