# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path


def apply_winner_decision_policy(model: dict[str, object], eligibility: dict[str, object], features: dict[str, object], output_dir: str | Path) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if eligibility.get("eligibility_class") == "DATA_BLOCKED" or model.get("model_status") == "WINNER_MODEL_BLOCKED":
        decision = "DATA_BLOCKED"
    elif features.get("source_quality_band") == "LOW":
        decision = "NO_DECISION"
    else:
        probs = {"HOME": float(model.get("home_win_probability", 0)), "DRAW": float(model.get("draw_probability", 0)), "AWAY": float(model.get("away_win_probability", 0))}
        top, second = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)[:2]
        edge = top[1] - second[1]
        conf = float(model.get("confidence", 0))
        if edge >= 0.12 and conf >= 0.68 and not (features.get("league_prediction_tier") == "TIER_2_RESULTS_ONLY" and features.get("xg_missing")):
            decision = "WINNER_PICK"
        elif edge >= 0.07 and conf >= 0.55:
            decision = "WINNER_LEAN"
        elif eligibility.get("eligibility_class") in {"NO_DECISION", "LEAN_ONLY"}:
            decision = "NO_DECISION" if edge < 0.07 else "WINNER_LEAN"
        else:
            decision = "NO_CLEAR_WINNER"
    result = {
        "decision_class": decision,
        "predicted_winner": model.get("predicted_winner", "NO_CLEAR_WINNER") if decision not in {"NO_DECISION", "DATA_BLOCKED"} else "NO_CLEAR_WINNER",
        "winner_team": model.get("winner_team", "") if decision not in {"NO_DECISION", "DATA_BLOCKED"} else "",
        "home_win_probability": model.get("home_win_probability", 0),
        "draw_probability": model.get("draw_probability", 0),
        "away_win_probability": model.get("away_win_probability", 0),
        "confidence": model.get("confidence", 0),
        "why": "Potential winner signal from as-of form/xG/model features." if decision in {"WINNER_PICK", "WINNER_LEAN"} else "No sufficiently clear winner signal.",
        "why_not_stronger": "Odds are optional; missing xG, weak source quality or small edge lowers confidence.",
        "missing_data": ", ".join(str(x) for x in model.get("missing_inputs", [])),
        "data_quality": features.get("source_quality_band", ""),
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }
    _write_outputs(out, result)
    return result


def _write_outputs(out: Path, result: dict[str, object]) -> None:
    (out / "winner_decision_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    card = "\n".join([
        "# v2.1 Winner Decision Card",
        "",
        f"Decision Class: {result['decision_class']}",
        f"Predicted Winner: {result['predicted_winner']}",
        f"Winner Team: {result['winner_team']}",
        f"Home/Draw/Away: {result['home_win_probability']} / {result['draw_probability']} / {result['away_win_probability']}",
        f"Confidence: {result['confidence']}",
        f"Why: {result['why']}",
        f"Why Not Stronger: {result['why_not_stronger']}",
        f"Missing Data: {result['missing_data']}",
        f"Data Quality: {result['data_quality']}",
        "",
        "Safety: no automatic betting, no stake, no ROI.",
        "",
    ])
    (out / "winner_decision_card.md").write_text(card, encoding="utf-8")
    (out / "winner_decision_audit.md").write_text("# v2.1 Winner Decision Audit\n\n" + json.dumps(result, indent=2), encoding="utf-8")
    result["winner_decision_result_path"] = str((out / "winner_decision_result.json").resolve())
    result["winner_decision_card_path"] = str((out / "winner_decision_card.md").resolve())
    result["winner_decision_audit_path"] = str((out / "winner_decision_audit.md").resolve())
