# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path

from football_prediction_v19.analysis.v20_historical_match_context import HistoricalMatchContext


def write_final_historical_analyst_report(context: HistoricalMatchContext, leakage: dict[str, object], merged: dict[str, object], features: dict[str, object], model: dict[str, object], decision: dict[str, object], output_dir: str | Path) -> str:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    path = out / "v20_final_historical_analyst_report.md"
    text = "\n".join([
        "# v2.0 Historical Internet Analyst Report",
        "",
        "## 1. Match Info", f"{context.home_team} vs {context.away_team} ({context.competition} {context.season})",
        "## 2. Analysis Cutoff", context.analysis_cutoff,
        "## 3. Sources Used", "football-data, Understat-style xG, historical odds",
        "## 4. Leakage Guard", str(leakage.get("leakage_status")),
        "## 5. Historical Table As-Of", f"table_available={merged.get('table_available')}",
        "## 6. Historical xG As-Of", f"xg_available={merged.get('xg_available')}",
        "## 7. Historical Odds As-Of", f"odds_available={merged.get('odds_1x2_available')}",
        "## 8. Feature Store Summary", str(features),
        "## 9. Model Probability Table", f"home={model.get('home_win_probability')} draw={model.get('draw_probability')} away={model.get('away_win_probability')}",
        "## 10. Main Edges", "As-of form/xG/market edge is summarized by the model.",
        "## 11. Main Risks", "Input quality and source coverage.",
        "## 12. Decision Gate", str(decision.get("decision_class")),
        "## 13. Final Tip Card", str(decision.get("primary_tip")),
        "## 14. No-Bet List", str(decision.get("no_bet_reasons", "")),
        "## 15. What Would Improve Confidence", "More recent form, lineup, injury and market snapshots.",
        "## 16. Safety Footer", "No automatic betting. No stake. No ROI. No guaranteed prediction.",
        "",
    ])
    path.write_text(text, encoding="utf-8")
    return str(path.resolve())
