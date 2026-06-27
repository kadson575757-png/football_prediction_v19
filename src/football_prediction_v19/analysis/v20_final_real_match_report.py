# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path


def write_v20_final_real_match_report(result: dict[str, object], output_dir: str | Path) -> str:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    context = result.get("match_context", {})
    path = out / "v20_final_real_match_report.md"
    lines = [
        _top_heading(result),
        "",
        "Block Reason:",
        *[f"- {reason}" for reason in result.get("block_reasons", [])],
        "",
        "Source Status:",
        *_source_lines(result),
        "",
        "Next Fix:",
        f"- {result.get('recommended_fix', 'Inspect source status and missing data.')}",
        "",
        "# v2.0 Final Real Match Report",
        "",
        "## 1. Match Input",
        f"{context.get('home_team')} vs {context.get('away_team')} on {context.get('match_date')} ({context.get('competition')} {context.get('season')})",
        "## 2. Fixture Resolution", str(result.get("fixture_resolution_status")),
        "## 3. Source League Mapping", str(result.get("source_league_mapping", {})),
        "## 4. Network / Cache Mode", f"network={str(result.get('network_calls_enabled')).lower()} cache_used={str(result.get('cache_used')).lower()}",
        "## 5. Sources Used", str(result.get("live_source_status")),
        "## 6. Source Quality Score", f"{result.get('source_quality_score')} ({result.get('source_quality_band')})",
        "## 7. Analysis Cutoff", str(result.get("analysis_cutoff")),
        "## 8. Leakage Guard", str(result.get("leakage_status")),
        "## 9. Historical Table/Form As-Of", f"table_available={result.get('table_available')}",
        "## 10. Historical xG As-Of", f"xg_available={result.get('xg_available')}",
        "## 11. Historical Odds As-Of", f"odds_available={result.get('odds_available')}",
        "## 12. Feature Store Summary", str(result.get("features", {})),
        "## 13. Model Probability Table", str(result.get("probabilities", {})),
        "## 14. Decision Gate", str(result.get("decision_class")),
        "## 15. Final Tip Card", f"primary_tip={result.get('primary_tip')} confidence={result.get('confidence')}",
        "## 16. No-Bet List", str(result.get("no_bet_reasons", "")),
        "## 17. Missing Data", str(result.get("missing_data", "")),
        "## 18. What Would Improve Confidence", "More source coverage, fresh cache, lineups, injuries, xG and odds snapshots.",
        "## 19. Safety Footer", "No automatic betting. No stake. No ROI. No guaranteed prediction.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path.resolve())


def _top_heading(result: dict[str, object]) -> str:
    decision = result.get("decision_class")
    if decision == "DATA_BLOCKED":
        return "# DATA_BLOCKED"
    if decision == "NO_BET":
        return "# NO_BET"
    if decision == "ANALYST_LEAN":
        return "# ANALYST_LEAN"
    return "# MODEL_TIP"


def _source_lines(result: dict[str, object]) -> list[str]:
    rows = []
    for provider, data in (result.get("source_status", {}) or {}).items():
        rows.append(f"- {provider}: {data.get('status')} - {data.get('reason')} cache_used={str(data.get('cache_used')).lower()} records={data.get('records_count')}")
    return rows or ["- source status unavailable"]
