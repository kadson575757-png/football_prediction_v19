#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from football_prediction_v19.prospective.result_import import import_results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Import results separately from locked predictions.")
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs/prospective_validation"))
    args = parser.parse_args(argv)
    result = import_results(args.output_dir, pd.read_csv(args.input_file, keep_default_na=False))
    for key, value in result.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
