# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from football_prediction_v19.analysis.real_match_artifact_acceptance_preview import RealMatchArtifactAcceptanceAuditor, RealMatchArtifactAcceptanceConfig  # noqa: E402


def audit_real_match_artifact_acceptance_preview(**kwargs: object) -> dict[str, object]:
    return RealMatchArtifactAcceptanceAuditor(RealMatchArtifactAcceptanceConfig(**kwargs)).run().__dict__


def main() -> int:
    result = audit_real_match_artifact_acceptance_preview(base_dir=ROOT)
    print(result["real_match_artifact_acceptance_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
