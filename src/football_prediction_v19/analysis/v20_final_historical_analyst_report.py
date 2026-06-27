# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path

from football_prediction_v19.analysis.v20_historical_match_context import HistoricalMatchContext


def write_final_historical_analyst_report(context: HistoricalMatchContext, leakage: dict[str, object], merged: dict[str, object], features: dict[str, object], model: dict[str, object], decision: dict[str, object], output_dir: str | Path, live_sources: dict[str, object] | None = None) -> str:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    path = out / "v20_final_historical_analyst_report.md"
    text = "\n".join([
        "# v2.0 Historical Internet Analyst Report",
        "",
        "## 1. Match Info", f"{context.home_team} vs {context.away_team} ({context.competition} {context.season})",
        "## 2. Analysis Cutoff", context.analysis_cutoff,
        "## 3. Live Sources Used", "football-data.co.uk, Understat, The Odds API when configured, API-Football optional",
        "## 3a. Source Status by Provider", _source_status(live_sources),
        "## 3b. Cache Status", f"cache_used={str((live_sources or {}).get('cache_used', False)).lower()}",
        "## 3c. API Key Presence", "Only key presence is reported; secret values are never written.",
        "## 3d. Source Coverage Matrix", f"table={merged.get('table_available')} xg={merged.get('xg_available')} odds={merged.get('odds_1x2_available')} lineups={features.get('lineups_available', False)} injuries={features.get('injuries_available', False)}",
        "## 4. Leakage Guard", str(leakage.get("leakage_status")),
        "## 5. Historical Table As-Of", f"table_available={merged.get('table_available')}",
        "## 6. Historical xG As-Of", f"xg_available={merged.get('xg_available')} source_quality={'available' if merged.get('xg_available') else 'missing_or_partial'}",
        "## 7. Historical Odds As-Of", f"odds_available={merged.get('odds_1x2_available')} snapshot_quality={'available' if merged.get('odds_1x2_available') else 'missing_or_partial'}",
        "## 7a. As-Of Cutoff Confirmation", f"All included source rows must be <= {context.analysis_cutoff}.",
        "## 7b. Leakage Exclusions", f"leakage_status={leakage.get('leakage_status')}",
        "## 8. Feature Store Summary", str(features),
        "## 9. Model Probability Table", f"home={model.get('home_win_probability')} draw={model.get('draw_probability')} away={model.get('away_win_probability')}",
        "## 10. Main Edges", "As-of form/xG/market edge is summarized by the model.",
        "## 11. Main Risks", "Input quality and source coverage.",
        "## 12. Model Policy Result", str(model.get("model_status")),
        "## 13. Decision Gate", str(decision.get("decision_class")),
        "## 14. Final Tip Card / No-Bet", str(decision.get("primary_tip")),
        "## 15. No-Bet List", str(decision.get("no_bet_reasons", "")),
        "## 16. What Would Improve Confidence", "More recent form, lineup, injury and market snapshots.",
        "## 17. Safety Footer", "No automatic betting. No stake. No ROI. No guaranteed prediction.",
        "",
    ])
    path.write_text(text, encoding="utf-8")
    return str(path.resolve())


def _source_status(live_sources: dict[str, object] | None) -> str:
    if not live_sources:
        return "mock/as-of mode; live source orchestrator not used"
    return " ".join(
        [
            f"live_source_status={live_sources.get('live_source_status')};",
            f"football_data={live_sources.get('football', {}).get('football_data_live_status')};",
            f"understat={live_sources.get('xg', {}).get('understat_live_status')};",
            f"odds_api={live_sources.get('odds', {}).get('odds_api_status')};",
            f"api_football={live_sources.get('api_football', {}).get('api_football_optional_status')}",
        ]
    )
