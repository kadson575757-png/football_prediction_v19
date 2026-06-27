# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path


REQUIRED_DOCS = [
    "docs/v20_historical_internet_prediction_engine.md",
    "docs/v20_live_source_adapter_activation.md",
    "docs/v20_real_match_autopilot_validation.md",
    "docs/v20_no_leakage_backtest.md",
    "docs/v20_one_command_user_workflow.md",
    "docs/v20_roadmap.md",
]


def run_v20_docs_consistency_check(repo_root: str | Path = ".") -> dict[str, object]:
    root = Path(repo_root)
    missing = [doc for doc in REQUIRED_DOCS if not (root / doc).exists()]
    return {"docs_consistency_status": "PASSED" if not missing else "FAILED", "missing_docs": missing}
