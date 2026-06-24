# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.build_final_real_match_analysis_readiness_preview_helper import build_final_real_match_analysis_readiness_preview_helper


def audit_final_real_match_analysis_readiness_preview() -> dict[str, object]:
    return build_final_real_match_analysis_readiness_preview_helper()


def main() -> int:
    result = audit_final_real_match_analysis_readiness_preview()
    print(result["final_real_match_analysis_readiness_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
