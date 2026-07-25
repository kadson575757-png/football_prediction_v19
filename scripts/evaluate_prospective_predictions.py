#!/usr/bin/env python
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from football_prediction_v19.prospective.evaluation import evaluate_prospective


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate locked primary and shadow predictions.")
    parser.add_argument("--output-dir", default=str(ROOT / "outputs/prospective_validation"))
    args = parser.parse_args(argv)
    result = evaluate_prospective(args.output_dir)
    for key, value in result.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
