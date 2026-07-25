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

from football_prediction_v19.prematch.input_schema import parse_match_input
from football_prediction_v19.prematch.unified_runner import analyze_match
from football_prediction_v19.prospective.prediction_store import lock_prediction


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Lock primary and shadow predictions before kickoff.")
    parser.add_argument("--input-file", required=True)
    parser.add_argument("--project-root", default=str(ROOT))
    parser.add_argument("--output-dir")
    args = parser.parse_args(argv)
    root = Path(args.project_root).resolve()
    out = Path(args.output_dir) if args.output_dir else root / "outputs/prospective_validation"
    rows = pd.read_csv(args.input_file, keep_default_na=False)
    completed, failed, conflicts = 0, 0, 0
    for _, row in rows.iterrows():
        try:
            match = parse_match_input(row.to_dict())
            prediction = analyze_match(
                match, project_root=root,
                output_base=out / "prematch_outputs",
                include_shadow_challenger=True, strict_asof=True,
            )
            locked = lock_prediction(
                out, match=match.as_dict(),
                kickoff_timestamp=str(row["kickoff_timestamp"]),
                prediction=prediction,
                fixture_id=str(row.get("fixture_id", "")) or None,
            )
            if locked["lock_operation_status"] == "LOCK_CONFLICT":
                conflicts += 1
                failed += 1
            else:
                completed += 1
        except Exception as exc:
            failed += 1
            print(f"fixture_error={exc}", file=sys.stderr)
    print("prospective_prediction_lock_status=" + ("READY" if completed else "FAILED"))
    print(f"rows_completed={completed}")
    print(f"rows_failed={failed}")
    print(f"lock_conflict_count={conflicts}")
    print("output_dir=" + str(out.resolve()))
    return 0 if completed else 1


if __name__ == "__main__":
    raise SystemExit(main())
