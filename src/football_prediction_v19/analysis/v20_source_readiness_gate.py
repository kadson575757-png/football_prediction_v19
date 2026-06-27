# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path


def evaluate_source_readiness(fixture_status: str, asof_status: str, leakage_status: str, coverage: dict[str, object], output_dir: str | Path | None = None) -> dict[str, object]:
    reasons: list[str] = []
    if fixture_status in {"NOT_FOUND", "AMBIGUOUS"}:
        readiness = "DATA_BLOCKED"; reasons.append(f"fixture {fixture_status.lower()}")
    elif leakage_status == "BLOCKED" or asof_status == "ASOF_BLOCKED":
        readiness = "DATA_BLOCKED"; reasons.append("leakage or as-of gate blocked")
    elif not coverage.get("table_available"):
        readiness = "DATA_BLOCKED"; reasons.append("table/form missing")
    elif not coverage.get("xg_available") or not coverage.get("odds_available"):
        readiness = "READY_FOR_ANALYST_LEAN" if fixture_status in {"RESOLVED", "PARTIAL"} else "NO_BET_REQUIRED"
        if not coverage.get("xg_available"):
            reasons.append("xG missing")
        if not coverage.get("odds_available"):
            reasons.append("odds missing")
    else:
        readiness = "READY_FOR_MODEL"
    result = {"source_readiness": readiness, "readiness_reasons": reasons}
    if output_dir is not None:
        out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
        (out / "v20_source_readiness_gate.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
