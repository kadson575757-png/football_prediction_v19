# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path


def compute_real_source_quality(fixture_status: str, coverage: dict[str, object], leakage_status: str, cache_used: bool = False, source_errors: int = 0, output_dir: str | Path | None = None) -> dict[str, object]:
    weights = {
        "fixture": 0.18 if fixture_status == "RESOLVED" else (0.10 if fixture_status == "PARTIAL" else 0.0),
        "table": 0.18 if coverage.get("table_available") else 0.0,
        "form": 0.08 if coverage.get("form_available", coverage.get("table_available")) else 0.0,
        "xg": 0.16 if coverage.get("xg_available") else 0.0,
        "player_xg": 0.06 if coverage.get("player_xg_available") else 0.0,
        "odds": 0.10 if coverage.get("odds_available") else 0.0,
        "no_odds_policy_credit": 0.06 if (coverage.get("xg_available") and not coverage.get("odds_available")) else 0.0,
        "cache": 0.06 if cache_used else 0.03,
        "agreement": 0.06 if coverage.get("table_available") and coverage.get("xg_available") else 0.0,
        "leakage": 0.06 if leakage_status == "CLEAN" else 0.0,
    }
    score = max(0.0, min(1.0, sum(weights.values()) - source_errors * 0.08))
    band = "HIGH" if score >= 0.85 else ("MEDIUM" if score >= 0.60 else ("LOW" if score >= 0.45 else "BLOCKED"))
    result = {"source_quality_score": round(score, 3), "source_quality_band": band, "quality_components": weights}
    if output_dir is not None:
        out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
        (out / "v20_real_source_quality_score.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        (out / "source_quality_report.md").write_text(f"# v2.0 Source Quality\n\n- score: {result['source_quality_score']}\n- band: {band}\n", encoding="utf-8")
    return result
