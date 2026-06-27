import pandas as pd

from football_prediction_v19.analysis.v20_cutoff_resolver import resolve_analysis_cutoff
from football_prediction_v19.analysis.v20_historical_match_context import build_match_context
from football_prediction_v19.analysis.v20_understat_xg_asof_adapter import build_understat_xg_asof


def test_understat_xg_asof_uses_prior_rows_only(tmp_path):
    matches = tmp_path / "understat.csv"
    pd.DataFrame(
        [
            {"date": "2025-08-01", "home_team": "Arsenal", "away_team": "Chelsea", "home_xg": 1.5, "away_xg": 1.0},
            {"date": "2026-02-14", "home_team": "Arsenal", "away_team": "Chelsea", "home_xg": 5.0, "away_xg": 5.0},
        ]
    ).to_csv(matches, index=False)
    players = tmp_path / "players.csv"
    pd.DataFrame(columns=["date", "player", "team", "minutes", "goals", "assists", "xg", "xa", "npxg"]).to_csv(players, index=False)
    context = resolve_analysis_cutoff(build_match_context("Arsenal", "Chelsea", "Premier League", "2025/26", "2026-02-14"))
    result = build_understat_xg_asof(matches, players, context, tmp_path / "out")
    table = pd.read_csv(result["understat_xg_asof_team_path"])
    arsenal = table[table["team"].eq("Arsenal")].iloc[0]
    assert arsenal["xg_for"] == 1.5
    assert result["xg_available"] is True
