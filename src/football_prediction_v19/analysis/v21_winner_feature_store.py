# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def build_winner_feature_store(selected_match: dict[str, object], asof_features: dict[str, object], eligibility: dict[str, object], source_quality: dict[str, object], output_dir: str | Path) -> dict[str, object]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    feat = {
        "canonical_match_id": selected_match.get("canonical_match_id", asof_features.get("match_id", "")),
        "league_prediction_tier": selected_match.get("prediction_tier", eligibility.get("prediction_tier", "")),
        "match_date": selected_match.get("match_date", ""),
        "home_team": selected_match.get("home_team", ""),
        "away_team": selected_match.get("away_team", ""),
        "home_points_per_game_asof": _num(asof_features.get("home_points_per_game_asof")),
        "away_points_per_game_asof": _num(asof_features.get("away_points_per_game_asof")),
        "table_rank_gap_asof": _num(asof_features.get("table_rank_gap_asof")),
        "home_recent_form_points_5": _num(asof_features.get("home_recent_form_points_5")),
        "away_recent_form_points_5": _num(asof_features.get("away_recent_form_points_5")),
        "home_recent_goals_for_5": _num(asof_features.get("home_recent_goals_for_5")),
        "away_recent_goals_for_5": _num(asof_features.get("away_recent_goals_for_5")),
        "home_recent_goals_against_5": _num(asof_features.get("home_recent_goals_against_5")),
        "away_recent_goals_against_5": _num(asof_features.get("away_recent_goals_against_5")),
        "home_xg_for_asof": _num(asof_features.get("home_xg_for_asof")),
        "away_xg_for_asof": _num(asof_features.get("away_xg_for_asof")),
        "home_xg_against_asof": _num(asof_features.get("home_xg_against_asof")),
        "away_xg_against_asof": _num(asof_features.get("away_xg_against_asof")),
        "xg_diff_edge_asof": _num(asof_features.get("xg_diff_edge_asof")),
        "home_rolling_xg_5": _num(asof_features.get("home_rolling_xg_5")),
        "away_rolling_xg_5": _num(asof_features.get("away_rolling_xg_5")),
        "home_implied_probability_asof": _num(asof_features.get("home_odds_implied_probability_asof")),
        "draw_implied_probability_asof": _num(asof_features.get("draw_odds_implied_probability_asof")),
        "away_implied_probability_asof": _num(asof_features.get("away_odds_implied_probability_asof")),
        "market_available": bool(asof_features.get("odds_available", False)),
        "source_quality_score": _num(source_quality.get("source_quality_score")),
        "source_quality_band": source_quality.get("source_quality_band", "LOW"),
        "early_season_risk": bool(asof_features.get("early_season_risk", False)),
        "xg_missing": not bool(asof_features.get("xg_available", False)),
        "odds_missing": not bool(asof_features.get("odds_available", False)),
        "fixture_resolution_risk": eligibility.get("eligibility_class") == "WINNER_MODEL_PARTIAL",
        "leakage_status": asof_features.get("leakage_status", "CLEAN"),
        "eligibility_class": eligibility.get("eligibility_class", ""),
    }
    feat["form_edge"] = feat["home_recent_form_points_5"] - feat["away_recent_form_points_5"]
    feat["goals_for_edge"] = feat["home_recent_goals_for_5"] - feat["away_recent_goals_for_5"]
    feat["goals_against_edge"] = feat["away_recent_goals_against_5"] - feat["home_recent_goals_against_5"]
    feat["xg_momentum_edge"] = feat["home_rolling_xg_5"] - feat["away_rolling_xg_5"]
    feat["xg_defensive_edge"] = feat["away_xg_against_asof"] - feat["home_xg_against_asof"]
    probs = {"HOME": feat["home_implied_probability_asof"], "DRAW": feat["draw_implied_probability_asof"], "AWAY": feat["away_implied_probability_asof"]}
    feat["market_favorite"] = max(probs.items(), key=lambda kv: kv[1])[0] if sum(probs.values()) > 0 else ""
    csv_path = out / "winner_feature_store.csv"
    json_path = out / "winner_feature_store.json"
    report_path = out / "winner_feature_store_report.md"
    pd.DataFrame([feat]).to_csv(csv_path, index=False)
    json_path.write_text(json.dumps(feat, indent=2), encoding="utf-8")
    report_path.write_text("# v2.1 Winner Feature Store\n\n" + pd.DataFrame([feat]).to_csv(index=False), encoding="utf-8")
    return {"winner_feature_store_status": "READY", "features": feat, "winner_feature_store_csv_path": str(csv_path.resolve()), "winner_feature_store_json_path": str(json_path.resolve()), "winner_feature_store_report_path": str(report_path.resolve())}


def _num(value: object) -> float:
    try:
        if value in (None, ""):
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
