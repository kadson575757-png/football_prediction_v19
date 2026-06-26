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

from football_prediction_v19.analysis.v19_decision_report_preview import V19DecisionReportConfig, V19DecisionReportRenderer  # noqa: E402


def build_v19_decision_report_preview(**kwargs: object) -> dict[str, object]:
    result, _report = V19DecisionReportRenderer(V19DecisionReportConfig(**kwargs)).run()
    return result.__dict__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-dir", default=str(ROOT))
    parser.add_argument("--output-dir", default=str(ROOT / "outputs" / "analysis_preview" / "v19_decision_report"))
    args = parser.parse_args(argv)
    summary = build_v19_decision_report_preview(base_dir=args.base_dir, output_dir=args.output_dir)
    for key, value in summary.items():
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
