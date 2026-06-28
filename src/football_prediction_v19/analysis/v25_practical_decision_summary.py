# -*- coding: utf-8 -*-
from __future__ import annotations


def build_practical_decision_summary(result: dict[str, object]) -> dict[str, str]:
    decision = str(result.get("decision_class", "NO_DECISION"))
    predicted = str(result.get("predicted_winner", "NO_CLEAR_WINNER"))
    confidence = _num(result.get("confidence"))
    risks = _risk_notes(result)
    if decision in {"WINNER_PICK", "WINNER_LEAN"} and predicted == "HOME":
        label = "Home Lean" if decision == "WINNER_LEAN" else "Home Pick"
        reason = f"{result.get('home_team', 'Home')} has the stronger winner profile in the current model read."
    elif decision in {"WINNER_PICK", "WINNER_LEAN"} and predicted == "AWAY":
        label = "Away Lean" if decision == "WINNER_LEAN" else "Away Pick"
        reason = f"{result.get('away_team', 'Away')} has the stronger winner profile in the current model read."
    elif decision == "NO_CLEAR_WINNER":
        label = "No Clear Winner"
        reason = "Probabilities are too close and no side has a clear enough edge."
    elif decision == "DATA_BLOCKED":
        label = "Data Blocked"
        reason = str(result.get("block_reason_text") or result.get("recommendation_summary") or "Required fixture or core data is unavailable.")
    else:
        label = "No Decision"
        reason = "Model ran, but confidence and edge did not meet the minimum decision threshold."
    return {
        "final_label": label,
        "user_facing_confidence": "High" if confidence >= 0.70 else ("Medium" if confidence >= 0.55 else "Low"),
        "short_reason": reason,
        "main_risk": risks[0] if risks else "No major additional risk note.",
        "data_quality_note": f"Source quality: {result.get('source_quality_band', 'UNKNOWN')}.",
    }


def _risk_notes(result: dict[str, object]) -> list[str]:
    notes = []
    if not _truthy(result.get("xg_available", False)):
        notes.append("xG missing, confidence is capped.")
    if not _truthy(result.get("odds_available", False)):
        notes.append("Odds missing, market context is unavailable.")
    if str(result.get("prediction_tier", "")).startswith("TIER_2"):
        notes.append("Results-only tier limits maximum decision strength.")
    if _num(result.get("confidence")) < 0.55:
        notes.append("Confidence is low.")
    return notes


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _num(value: object) -> float:
    try:
        if str(value).strip() == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
