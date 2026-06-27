# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path


def compute_real_source_quality(fixture_status: str, coverage: dict[str, object], leakage_status: str, cache_used: bool = False, source_errors: int = 0, output_dir: str | Path | None = None) -> dict[str, object]:
    breakdown = {
        "fixture_score": 0.20 if fixture_status == "RESOLVED" else (0.12 if fixture_status == "PARTIAL" else 0.0),
        "table_form_score": (0.18 if coverage.get("table_available") else 0.0) + (0.10 if coverage.get("form_available", coverage.get("table_available")) else 0.0),
        "xg_score": 0.20 if coverage.get("xg_available") else 0.0,
        "player_xg_score": 0.04 if coverage.get("player_xg_available") else 0.0,
        "odds_score": 0.08 if coverage.get("odds_available") else 0.0,
        "no_odds_policy_credit": 0.08 if (coverage.get("xg_available") and not coverage.get("odds_available")) else 0.0,
        "cache_score": 0.06 if cache_used else 0.03,
        "agreement_score": 0.06 if coverage.get("table_available") and coverage.get("xg_available") else 0.0,
        "leakage_score": 0.06 if leakage_status == "CLEAN" else 0.0,
        "missing_data_penalty": source_errors * 0.08,
    }
    score = max(0.0, min(1.0, sum(v for k, v in breakdown.items() if k != "missing_data_penalty") - breakdown["missing_data_penalty"]))
    band = "HIGH" if score >= 0.85 else ("MEDIUM" if score >= 0.60 else ("LOW" if score >= 0.45 else "BLOCKED"))
    result = {"source_quality_score": round(score, 3), "source_quality_band": band, "quality_components": breakdown, "source_quality_breakdown": {**breakdown, "final_score": round(score, 3), "final_band": band}}
    if output_dir is not None:
        out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
        (out / "v20_real_source_quality_score.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        (out / "source_quality_report.md").write_text("# v2.0 Source Quality\n\n" + "\n".join(f"- {k}: {v}" for k, v in result["source_quality_breakdown"].items()) + "\n", encoding="utf-8")
    return result
