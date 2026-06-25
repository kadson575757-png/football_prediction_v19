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

from football_prediction_v19.analysis.real_match_analysis_runner_preview import RealMatchAnalysisRunner, RealMatchAnalysisRunnerConfig  # noqa: E402


def build_real_match_analysis_runner_preview(**kwargs: object) -> dict[str, object]:
    return RealMatchAnalysisRunner(RealMatchAnalysisRunnerConfig(**kwargs)).run().__dict__


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-match-intake", required=True)
    parser.add_argument("--manual-evidence-completion", default=None)
    parser.add_argument("--output-dir", default="outputs/analysis_preview/real_match_analysis_runner")
    args = parser.parse_args()
    summary = build_real_match_analysis_runner_preview(
        real_match_intake_path=args.real_match_intake,
        manual_evidence_completion_path=args.manual_evidence_completion,
        output_dir=args.output_dir,
        base_dir=ROOT,
    )
    for key, value in summary.items():
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
