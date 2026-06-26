# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.analysis.v19_final_release_readiness_gate_preview import run_final_release_readiness_gate  # noqa: E402


def run_v19_final_release_readiness_gate_preview(**kwargs: object) -> dict[str, object]:
    return run_final_release_readiness_gate(kwargs["final_pipeline_results_json"], kwargs.get("output_dir", ROOT / "outputs" / "analysis_preview" / "v19_final_pipeline" / "final_reports"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final-pipeline-results-json", required=True)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "v19_final_release_readiness_gate"))
    args = parser.parse_args(argv)
    result = run_v19_final_release_readiness_gate_preview(final_pipeline_results_json=args.final_pipeline_results_json, output_dir=args.output_dir)
    for key, value in result.items():
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
