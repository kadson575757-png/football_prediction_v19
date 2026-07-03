import pandas as pd

from football_prediction_v19.analysis.v2107_league_zone_pressure_indicator import build_league_zone_pressure_indicator


def test_league_zone_pressure_indicator_builds_table_before_match(monkeypatch):
    rows = []
    teams = ["City", "Liverpool", "Spurs", "Villa", "United", "Brighton", "Everton", "Burnley", "Forest"]
    for i in range(9):
        rows.append({"match_date": f"2026-01-{i+1:02d}", "home_team": "Arsenal", "away_team": teams[i], "home_goals": 3, "away_goals": 0})
        rows.append({"match_date": f"2026-02-{i+1:02d}", "home_team": teams[i], "away_team": "Chelsea", "home_goals": 2, "away_goals": 0})
    rows.append({"match_date": "2026-03-01", "home_team": "Arsenal", "away_team": "Chelsea", "home_goals": 0, "away_goals": 9})
    frame = pd.DataFrame(rows)
    monkeypatch.setattr("football_prediction_v19.analysis.v2107_league_zone_pressure_indicator._load_match_rows", lambda *args, **kwargs: frame)

    result = build_league_zone_pressure_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-03-01", 0.4, 0.3, 0.3)

    assert result["lzp_home_points_before_match"] == 27
    assert result["lzp_away_points_before_match"] == 0
    assert result["lzp_home_rank_before_match"] == 1
    assert result["lzp_home_zone"] == "title_zone"
    assert result["lzp_away_zone"] == "relegation_zone"
    assert result["lzp_season_phase"] == "early"
    assert result["lzp_pressure_signal"] > 0
