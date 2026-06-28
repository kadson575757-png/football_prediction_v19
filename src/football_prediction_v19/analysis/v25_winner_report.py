# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

from football_prediction_v19.analysis.v25_practical_decision_summary import build_practical_decision_summary


def render_winner_markdown_report(result: dict[str, object]) -> str:
    summary = build_practical_decision_summary(result)
    home = result.get("home_team", "Home")
    away = result.get("away_team", "Away")
    risks = result.get("risk_notes", [])
    reasons = result.get("primary_reasons", [])
    if isinstance(risks, str):
        risks = [x.strip() for x in risks.split(";") if x.strip()]
    if isinstance(reasons, str):
        reasons = [x.strip() for x in reasons.split(";") if x.strip()]
    return "\n".join([
        f"# Winner Analysis: {home} vs {away}",
        "",
        "## Entscheidung",
        "",
        f"* Decision Class: {result.get('decision_class', '')}",
        f"* Predicted Winner: {result.get('predicted_winner', '')}",
        f"* Confidence: {result.get('confidence', '')}",
        f"* Risk Level: {result.get('risk_level', '')}",
        "",
        "## 1X2 Wahrscheinlichkeiten",
        "",
        "| Ergebnis | Wahrscheinlichkeit |",
        "| --- | ---: |",
        f"| Home | {result.get('home_win_probability', 0)} |",
        f"| Draw | {result.get('draw_probability', 0)} |",
        f"| Away | {result.get('away_win_probability', 0)} |",
        "",
        "## Warum?",
        "",
        *(f"* {reason}" for reason in (reasons or ["Current form and source-quality signals were evaluated."])),
        "",
        "## Risiken",
        "",
        *(f"* {risk}" for risk in (risks or ["No extra risk note."])),
        "",
        "## Fazit",
        "",
        summary["short_reason"],
        "",
        "Safety: winner analysis only. No automatic action, no stake, no ROI.",
        "",
    ])


def write_winner_report(result: dict[str, object], output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "winner_analysis.json"
    md_path = out / "winner_analysis.md"
    txt_path = out / "winner_analysis_summary.txt"
    json_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    md_path.write_text(render_winner_markdown_report(result), encoding="utf-8")
    txt_path.write_text(str(result.get("recommendation_summary", "")), encoding="utf-8")
    return {
        "winner_analysis_json_path": str(json_path.resolve()),
        "winner_analysis_markdown_path": str(md_path.resolve()),
        "winner_analysis_summary_path": str(txt_path.resolve()),
    }
