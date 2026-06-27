import pandas as pd

from football_prediction_v19.analysis.v20_asof_feature_store import build_asof_feature_store
from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context
from football_prediction_v19.analysis.v20_understat_xg_asof_adapter import build_understat_xg_asof


def test_v202_understat_xg_reaches_feature_store(tmp_path):
    context = resolve_analysis_cutoff(build_match_context("Arsenal", "Leeds", "Premier League", "2025/26", "2025-08-23"))
    xg_csv = tmp_path / "xg.csv"
    pd.DataFrame([
        {"date": "2025-08-10", "home_team": "Arsenal", "away_team": "Leeds United", "home_xg": 2.0, "away_xg": 0.8}
    ]).to_csv(xg_csv, index=False)
    players = tmp_path / "players.csv"
    pd.DataFrame(columns=["date", "player", "team", "minutes", "goals", "assists", "xg", "xa", "npxg"]).to_csv(players, index=False)
    xg = build_understat_xg_asof(xg_csv, players, context, tmp_path / "xgout")
    football = _football_paths(tmp_path)
    odds = _odds_paths(tmp_path)
    merged = {"table_available": True, "xg_available": True, "odds_1x2_available": False, "leakage_clean": True}
    store = build_asof_feature_store(context, football, xg, odds, merged, tmp_path / "store")
    assert store["features"]["home_xg_for_asof"] > 0
    assert store["features"]["away_xg_for_asof"] > 0


def _football_paths(tmp_path):
    table = tmp_path / "table.csv"; form = tmp_path / "form.csv"; report = tmp_path / "football.md"
    pd.DataFrame([{"team": "Arsenal", "points_per_game": 2.0}, {"team": "Leeds", "points_per_game": 1.0}]).to_csv(table, index=False)
    pd.DataFrame([{"team": "Arsenal", "recent_form_points_5": 10}, {"team": "Leeds", "recent_form_points_5": 5}]).to_csv(form, index=False)
    report.write_text("", encoding="utf-8")
    return {"football_data_asof_table_path": str(table), "football_data_asof_form_path": str(form), "football_data_asof_report_path": str(report)}


def _odds_paths(tmp_path):
    odds = tmp_path / "odds.csv"; report = tmp_path / "odds.md"
    pd.DataFrame(columns=["market", "selection", "implied_probability"]).to_csv(odds, index=False)
    report.write_text("", encoding="utf-8")
    return {"odds_asof_clean_path": str(odds), "odds_asof_report_path": str(report)}
