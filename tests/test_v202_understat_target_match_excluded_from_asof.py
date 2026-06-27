import pandas as pd

from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context
from football_prediction_v19.analysis.v20_understat_xg_asof_adapter import build_understat_xg_asof


def test_v202_understat_target_match_excluded_from_asof(tmp_path):
    context = resolve_analysis_cutoff(build_match_context("Arsenal", "Leeds", "Premier League", "2025/26", "2025-08-23"))
    xg_csv = tmp_path / "xg.csv"
    pd.DataFrame([
        {"date": "2025-08-10", "home_team": "Arsenal", "away_team": "Leeds United", "home_xg": 2.0, "away_xg": 0.8},
        {"date": "2025-08-23", "home_team": "Arsenal", "away_team": "Leeds United", "home_xg": 9.0, "away_xg": 9.0},
    ]).to_csv(xg_csv, index=False)
    players = tmp_path / "players.csv"
    pd.DataFrame(columns=["date", "player", "team", "minutes", "goals", "assists", "xg", "xa", "npxg"]).to_csv(players, index=False)
    result = build_understat_xg_asof(xg_csv, players, context, tmp_path / "out")
    table = pd.read_csv(result["understat_xg_asof_team_path"])
    arsenal = table[table["team"].eq("Arsenal")].iloc[0]
    assert arsenal["xg_for"] == 2.0
