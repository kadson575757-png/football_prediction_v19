# -*- coding: utf-8 -*-
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError


def load_results(path: str | Path) -> pd.DataFrame:
    if not Path(path).exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, keep_default_na=False)
    except EmptyDataError:
        return pd.DataFrame()


def enrich_prediction_frame(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, row in frame.iterrows():
        probs = {
            "HOME": _num(row.get("home_win_probability")),
            "DRAW": _num(row.get("draw_probability")),
            "AWAY": _num(row.get("away_win_probability")),
        }
        ordered = sorted(probs.items(), key=lambda item: item[1], reverse=True)
        top, second = ordered[0], ordered[1]
        actual = str(row.get("actual_result", row.get("result_1x2", ""))).strip()
        actual_key = {"H": "HOME", "D": "DRAW", "A": "AWAY"}.get(actual, "")
        brier = sum((probs[key] - (1.0 if key == actual_key else 0.0)) ** 2 for key in probs) / 3 if actual_key else 0.0
        entropy = -sum(p * math.log(p, 2) for p in probs.values() if p > 0)
        xg_available = _truthy(row.get("xg_available", False))
        odds_available = _truthy(row.get("odds_available", False))
        early = _truthy(row.get("early_season_risk", False))
        confidence = _num(row.get("confidence"))
        tier = str(row.get("prediction_tier", row.get("league_prediction_tier", "")))
        no_xg_partial = str(row.get("model_status", "")) == "WINNER_MODEL_PARTIAL" and not xg_available
        cap_applied = no_xg_partial or early or not odds_available
        cap_reason = ";".join(reason for reason, active in [("MISSING_XG_CAP", no_xg_partial), ("EARLY_SEASON_RISK", early), ("MISSING_ODDS_PENALTY", not odds_available)] if active)
        rows.append({
            "canonical_match_id": row.get("match_id", row.get("canonical_match_id", "")),
            "competition": row.get("competition", row.get("league", "")),
            "season": row.get("season", ""),
            "match_date": row.get("match_date", row.get("prediction_date", "")),
            "home_team": row.get("home_team", ""),
            "away_team": row.get("away_team", ""),
            "result_1x2": actual,
            "predicted_top_class": top[0],
            "predicted_top_team": _predicted_team(top[0], row),
            "home_win_probability": probs["HOME"],
            "draw_probability": probs["DRAW"],
            "away_win_probability": probs["AWAY"],
            "top_probability": top[1],
            "second_probability": second[1],
            "top_edge": top[1] - second[1],
            "home_draw_edge": probs["HOME"] - probs["DRAW"],
            "away_draw_edge": probs["AWAY"] - probs["DRAW"],
            "home_away_edge": probs["HOME"] - probs["AWAY"],
            "confidence": confidence,
            "confidence_band": "HIGH" if confidence >= 0.72 else ("MEDIUM" if confidence >= 0.55 else "LOW"),
            "source_quality_band": row.get("source_quality_band", ""),
            "eligibility_class": row.get("eligibility_class", ""),
            "model_status": row.get("model_status", ""),
            "decision_class": row.get("decision_class", ""),
            "no_decision_reason": row.get("no_decision_reason", ""),
            "xg_available": xg_available,
            "odds_available": odds_available,
            "table_form_available": True,
            "early_season_risk": early,
            "prediction_tier": tier,
            "no_xg_partial_model": no_xg_partial,
            "confidence_cap_applied": cap_applied,
            "confidence_cap_reason": cap_reason,
            "top1_correct": bool(actual_key and top[0] == actual_key),
            "probability_assigned_to_actual_result": probs.get(actual_key, 0.0),
            "brier_score_row": brier,
            "probability_entropy": entropy,
            "favorite_bias_flag": top[0] in {"HOME", "AWAY"} and top[1] > 0.45,
            "draw_compression_flag": abs(probs["DRAW"] - 0.3333) < 0.04,
        })
    return pd.DataFrame(rows)


def _predicted_team(top_class: str, row: pd.Series) -> str:
    if top_class == "HOME":
        return str(row.get("home_team", ""))
    if top_class == "AWAY":
        return str(row.get("away_team", ""))
    return "Draw"


def _num(value: object) -> float:
    try:
        if str(value).strip() == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}
