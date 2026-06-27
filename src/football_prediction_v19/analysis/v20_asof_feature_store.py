# -*- coding: utf-8 -*-
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

from football_prediction_v19.analysis.v20_historical_match_context import HistoricalMatchContext


def build_asof_feature_store(context: HistoricalMatchContext, football: dict[str, object], xg: dict[str, object], odds: dict[str, object], merged: dict[str, object], output_dir: str | Path) -> dict[str, object]:
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    table = pd.read_csv(football["football_data_asof_table_path"], keep_default_na=False)
    form = pd.read_csv(football["football_data_asof_form_path"], keep_default_na=False)
    xgf = pd.read_csv(xg["understat_xg_asof_team_path"], keep_default_na=False)
    oddsf = pd.read_csv(odds["odds_asof_clean_path"], keep_default_na=False)
    def row(df, col, val): 
        hit = df[df[col].eq(val)]
        return hit.iloc[0].to_dict() if not hit.empty else {}
    ht, at = row(table, "team", context.home_team), row(table, "team", context.away_team)
    hf, af = row(form, "team", context.home_team), row(form, "team", context.away_team)
    hx, ax = row(xgf, "team", context.home_team), row(xgf, "team", context.away_team)
    probs = {r["selection"]: float(r["implied_probability"]) for _, r in oddsf[oddsf["market"].eq("1X2")].iterrows()}
    totals = {r["selection"]: float(r["implied_probability"]) for _, r in oddsf[oddsf["market"].eq("OU25")].iterrows()}
    quality = round(sum(bool(merged.get(k)) for k in ["table_available", "xg_available", "odds_1x2_available"]) / 3, 2)
    feat = {"match_id": context.match_id, "home_points_per_game_asof": ht.get("points_per_game", 0), "away_points_per_game_asof": at.get("points_per_game", 0), "table_rank_gap_asof": int(table.index[table["team"].eq(context.away_team)][0]) - int(table.index[table["team"].eq(context.home_team)][0]) if not table.empty and context.home_team in set(table["team"]) and context.away_team in set(table["team"]) else 0, "home_recent_form_points_5": hf.get("recent_form_points_5", 0), "away_recent_form_points_5": af.get("recent_form_points_5", 0), "home_recent_goals_for_5": hf.get("recent_goals_for_5", 0), "away_recent_goals_for_5": af.get("recent_goals_for_5", 0), "home_recent_goals_against_5": hf.get("recent_goals_against_5", 0), "away_recent_goals_against_5": af.get("recent_goals_against_5", 0), "home_xg_for_asof": hx.get("xg_for", 0), "away_xg_for_asof": ax.get("xg_for", 0), "home_xg_against_asof": hx.get("xg_against", 0), "away_xg_against_asof": ax.get("xg_against", 0), "xg_diff_edge_asof": float(hx.get("xg_diff", 0) or 0) - float(ax.get("xg_diff", 0) or 0), "home_rolling_xg_5": hx.get("rolling_xg_for_5", 0), "away_rolling_xg_5": ax.get("rolling_xg_for_5", 0), "home_odds_implied_probability_asof": probs.get("HOME", 0), "draw_odds_implied_probability_asof": probs.get("DRAW", 0), "away_odds_implied_probability_asof": probs.get("AWAY", 0), "over25_implied_probability_asof": totals.get("OVER_2_5", 0), "under25_implied_probability_asof": totals.get("UNDER_2_5", 0), "table_available": merged.get("table_available", False), "xg_available": merged.get("xg_available", False), "odds_available": merged.get("odds_1x2_available", False), "leakage_status": "CLEAN" if merged.get("leakage_clean") else "BLOCKED", "data_quality_score": quality}
    csv_path = out / "asof_feature_store.csv"; json_path = out / "asof_feature_store.json"; report = out / "asof_feature_store_report.md"
    pd.DataFrame([feat]).to_csv(csv_path, index=False); json_path.write_text(json.dumps(feat, indent=2), encoding="utf-8")
    report.write_text("# v2.0 As-Of Feature Store Report\n\n" + pd.DataFrame([feat]).to_csv(index=False) + "\n", encoding="utf-8")
    return {"asof_feature_store_status": "READY", "features": feat, "asof_feature_store_csv_path": str(csv_path.resolve()), "asof_feature_store_json_path": str(json_path.resolve()), "asof_feature_store_report_path": str(report.resolve())}
