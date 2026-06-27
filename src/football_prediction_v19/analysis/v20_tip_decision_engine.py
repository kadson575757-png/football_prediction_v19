# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from pathlib import Path


def run_tip_decision_engine(model: dict[str, object], asof_status: str, features: dict[str, object], output_dir: str | Path) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    if model.get("model_status") == "MODEL_BLOCKED" or asof_status == "ASOF_BLOCKED":
        decision, tip = "DATA_BLOCKED", "NO_BET"
    elif float(features.get("data_quality_score", 0)) < 0.6:
        decision, tip = "NO_BET", "NO_BET"
    elif model.get("model_status") == "MODEL_PARTIAL" and not features.get("xg_available"):
        decision, tip = ("NO_BET", "NO_BET") if float(model.get("model_confidence", 0)) < 0.6 else ("ANALYST_LEAN", "NO_BET")
    elif model.get("model_status") == "MODEL_PARTIAL" and not features.get("odds_available") and float(model.get("model_confidence", 0)) < 0.6:
        decision, tip = "NO_BET", "NO_BET"
    elif features.get("source_conflict_high"):
        decision, tip = "NO_BET", "NO_BET"
    else:
        probs = {"1X2_HOME": model.get("home_win_probability", 0), "DOUBLE_CHANCE_HOME_DRAW": float(model.get("home_win_probability", 0)) + float(model.get("draw_probability", 0)), "1X2_AWAY": model.get("away_win_probability", 0), "DOUBLE_CHANCE_AWAY_DRAW": float(model.get("away_win_probability", 0)) + float(model.get("draw_probability", 0))}
        tip, best = max(probs.items(), key=lambda kv: kv[1])
        decision = "MODEL_TIP" if float(model.get("model_confidence", 0)) >= 0.7 and best >= 0.55 else "ANALYST_LEAN"
        if not features.get("odds_available") and decision == "MODEL_TIP" and float(model.get("model_confidence", 0)) < 0.78:
            decision = "ANALYST_LEAN"
    missing = ", ".join(str(x) for x in model.get("missing_inputs", []))
    why = "As-of fixture, table/form and xG support this preview decision." if tip != "NO_BET" else "Coverage, confidence or leakage policy prevents a production recommendation."
    if not features.get("odds_available"):
        why += " Odds unavailable because no API key was provided; odds are optional in v2.0.1."
    result = {"decision_class": decision, "primary_tip": tip, "secondary_tip": "", "confidence": model.get("model_confidence", 0), "risk_level": "HIGH" if float(model.get("model_risk_score", 1)) > 0.5 else "MEDIUM", "why": why, "why_not_stronger": "No stake, ROI or automatic betting; confidence depends on source coverage.", "missing_data": missing, "no_bet_reasons": "Data quality, missing source coverage or leakage gate blocked." if tip == "NO_BET" else "", "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}
    (out / "v20_tip_decision_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    card = "\n".join(["# v2.0 Tip Decision Card", "", f"- decision_class: {decision}", f"- primary_tip: {tip}", f"- confidence: {result['confidence']}", f"- risk_level: {result['risk_level']}", f"- why: {result['why']}", f"- why_not_stronger: {result['why_not_stronger']}", "", "No automatic betting. No stake. No ROI.", ""])
    (out / "v20_tip_decision_card.md").write_text(card, encoding="utf-8")
    (out / "v20_tip_decision_audit.md").write_text("# v2.0 Tip Decision Audit\n\n" + json.dumps(result, indent=2), encoding="utf-8")
    result.update({"v20_tip_decision_result_path": str((out / "v20_tip_decision_result.json").resolve()), "v20_tip_decision_card_path": str((out / "v20_tip_decision_card.md").resolve()), "v20_tip_decision_audit_path": str((out / "v20_tip_decision_audit.md").resolve())})
    return result
