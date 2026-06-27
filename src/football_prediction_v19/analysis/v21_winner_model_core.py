# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def run_winner_model_core(features: dict[str, object], eligibility: dict[str, object], output_dir: str | Path) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if eligibility.get("eligibility_class") == "DATA_BLOCKED":
        result = _blocked("eligibility data blocked")
    else:
        home_strength = 0.34 + _num(features.get("form_edge")) * 0.012 + _num(features.get("goals_for_edge")) * 0.01 + _num(features.get("goals_against_edge")) * 0.008 + 0.035
        away_strength = 0.33 - _num(features.get("form_edge")) * 0.012 - _num(features.get("goals_for_edge")) * 0.01 - _num(features.get("goals_against_edge")) * 0.008
        draw_strength = 0.29
        if not features.get("xg_missing", True):
            xg_edge = _num(features.get("xg_diff_edge_asof")) + _num(features.get("xg_momentum_edge")) * 0.15 + _num(features.get("xg_defensive_edge")) * 0.1
            home_strength += xg_edge * 0.025
            away_strength -= xg_edge * 0.025
        if features.get("market_available"):
            home_strength = home_strength * 0.75 + _num(features.get("home_implied_probability_asof")) * 0.25
            draw_strength = draw_strength * 0.75 + _num(features.get("draw_implied_probability_asof")) * 0.25
            away_strength = away_strength * 0.75 + _num(features.get("away_implied_probability_asof")) * 0.25
        probs = _normalize(home_strength, draw_strength, away_strength)
        top, second = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)[:2]
        confidence = 0.45 + (top[1] - second[1]) * 1.2 + _num(features.get("source_quality_score")) * 0.25
        missing = []
        if features.get("xg_missing"):
            confidence = min(confidence, 0.62); missing.append("xg")
        if features.get("odds_missing"):
            confidence -= 0.04; missing.append("odds")
        if features.get("league_prediction_tier") == "TIER_2_RESULTS_ONLY":
            confidence = min(confidence, 0.62)
        if features.get("early_season_risk"):
            confidence = min(confidence, 0.55); missing.append("early_season_sample")
        confidence = round(max(0.0, min(0.88, confidence)), 3)
        predicted = top[0] if top[1] - second[1] >= 0.03 else "NO_CLEAR_WINNER"
        result = {
            "home_win_probability": round(probs["HOME"], 4),
            "draw_probability": round(probs["DRAW"], 4),
            "away_win_probability": round(probs["AWAY"], 4),
            "predicted_winner": predicted,
            "winner_team": _winner_team(predicted, features),
            "confidence": confidence,
            "confidence_band": "HIGH" if confidence >= 0.72 else ("MEDIUM" if confidence >= 0.55 else "LOW"),
            "model_status": "WINNER_MODEL_READY" if eligibility.get("eligibility_class") == "WINNER_MODEL_READY" else "WINNER_MODEL_PARTIAL",
            "main_edges": _main_edges(features),
            "main_risks": _main_risks(features),
            "missing_inputs": missing,
            "automatic_betting_enabled": False,
            "staking_logic_enabled": False,
            "roi_logic_enabled": False,
        }
    _write_outputs(out, result)
    return result


def _blocked(reason: str) -> dict[str, object]:
    return {"home_win_probability": 0.0, "draw_probability": 0.0, "away_win_probability": 0.0, "predicted_winner": "NO_CLEAR_WINNER", "winner_team": "", "confidence": 0.0, "confidence_band": "LOW", "model_status": "WINNER_MODEL_BLOCKED", "main_edges": [], "main_risks": [reason], "missing_inputs": [reason], "automatic_betting_enabled": False, "staking_logic_enabled": False, "roi_logic_enabled": False}


def _normalize(home: float, draw: float, away: float) -> dict[str, float]:
    vals = [max(0.08, home), max(0.16, draw), max(0.08, away)]
    total = sum(vals)
    return {"HOME": vals[0] / total, "DRAW": vals[1] / total, "AWAY": vals[2] / total}


def _winner_team(predicted: str, features: dict[str, object]) -> str:
    if predicted == "HOME":
        return str(features.get("home_team", ""))
    if predicted == "AWAY":
        return str(features.get("away_team", ""))
    if predicted == "DRAW":
        return "Draw"
    return ""


def _main_edges(features: dict[str, object]) -> list[str]:
    edges = []
    if _num(features.get("form_edge")) > 0:
        edges.append("home form edge")
    if _num(features.get("form_edge")) < 0:
        edges.append("away form edge")
    if not features.get("xg_missing"):
        edges.append("xG edge available")
    return edges


def _main_risks(features: dict[str, object]) -> list[str]:
    risks = []
    if features.get("xg_missing"):
        risks.append("xG missing")
    if features.get("odds_missing"):
        risks.append("odds missing optional")
    if features.get("early_season_risk"):
        risks.append("early season sample")
    return risks


def _write_outputs(out: Path, result: dict[str, object]) -> None:
    (out / "winner_model_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    pd.DataFrame([
        {"selection": "HOME", "probability": result["home_win_probability"]},
        {"selection": "DRAW", "probability": result["draw_probability"]},
        {"selection": "AWAY", "probability": result["away_win_probability"]},
    ]).to_csv(out / "winner_probability_table.csv", index=False)
    (out / "winner_model_report.md").write_text("# v2.1 Winner Model Report\n\n" + json.dumps(result, indent=2), encoding="utf-8")
    result["winner_model_result_path"] = str((out / "winner_model_result.json").resolve())
    result["winner_probability_table_path"] = str((out / "winner_probability_table.csv").resolve())
    result["winner_model_report_path"] = str((out / "winner_model_report.md").resolve())


def _num(value: object) -> float:
    try:
        if value in (None, ""):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
