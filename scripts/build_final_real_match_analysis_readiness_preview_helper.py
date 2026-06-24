# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.analysis.final_real_match_analysis_readiness_preview import FinalRealMatchAnalysisReadinessAuditor, FinalRealMatchAnalysisReadinessConfig  # noqa: E402


def build_final_real_match_analysis_readiness_preview_helper() -> dict[str, object]:
    return FinalRealMatchAnalysisReadinessAuditor(FinalRealMatchAnalysisReadinessConfig(base_dir=ROOT)).run().__dict__


def main() -> int:
    summary = build_final_real_match_analysis_readiness_preview_helper()
    for key, value in summary.items():
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
