# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path


def evaluate_prediction_eligibility(resolution: dict[str, object], coverage: dict[str, object], asof: dict[str, object], output_dir: str | Path | None = None) -> dict[str, object]:
    reasons: list[str] = []
    status = str(resolution.get("status", "NOT_FOUND"))
    tier = str(coverage.get("prediction_tier", "UNSUPPORTED"))
    prior_matches = int(coverage.get("prior_matches_count", 5) or 0)
    if status in {"NOT_FOUND", "AMBIGUOUS"}:
        eligibility = "DATA_BLOCKED"; reasons.append("fixture unresolved or ambiguous")
    elif asof.get("leakage_status") == "BLOCKED":
        eligibility = "DATA_BLOCKED"; reasons.append("leakage blocked")
    elif not coverage.get("table_available", coverage.get("table_form_available", False)):
        eligibility = "DATA_BLOCKED"; reasons.append("table/form missing")
    elif prior_matches < int(coverage.get("min_prior_matches", 2)):
        eligibility = "LEAN_ONLY"; reasons.append("early season risk")
    elif tier == "TIER_1_FULL_XG" and coverage.get("xg_available"):
        eligibility = "WINNER_MODEL_READY" if status == "RESOLVED" else "WINNER_MODEL_PARTIAL"
    elif tier == "TIER_1_FULL_XG":
        eligibility = "LEAN_ONLY"; reasons.append("xG missing")
    elif tier == "TIER_2_RESULTS_ONLY":
        eligibility = "LEAN_ONLY"; reasons.append("results-only league tier")
    elif tier == "TIER_3_LIMITED":
        eligibility = "NO_DECISION"; reasons.append("limited source coverage")
    else:
        eligibility = "DATA_BLOCKED"; reasons.append("unsupported league")
    if not coverage.get("odds_available", False):
        reasons.append("odds missing optional")
    result = {"eligibility_class": eligibility, "eligibility_reasons": reasons, "prediction_tier": tier, "odds_required": False}
    if output_dir is not None:
        out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
        (out / "prediction_eligibility_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        (out / "prediction_eligibility_report.md").write_text("# v2.1 Prediction Eligibility\n\n" + "\n".join(f"- {k}: {v}" for k, v in result.items()) + "\n", encoding="utf-8")
    return result
