import pandas as pd

from football_prediction_v19.analysis.v2108_strength_band_performance_indicator import build_strength_band_performance_indicator


def test_strength_band_performance_uses_target_zones_and_excludes_match_date(monkeypatch):
    rows = []
    strong = ["Arsenal", "City", "Liverpool"]
    weak = ["Chelsea", "Burnley", "Forest"]
    mids = ["Spurs", "Villa", "United", "Brighton"]
    for i, opp in enumerate(strong[1:] + mids + weak, start=1):
        rows.append({"match_date": f"2026-01-{i:02d}", "home_team": "Arsenal", "away_team": opp, "home_goals": 3, "away_goals": 0})
    for i, opp in enumerate(strong + mids + weak[1:], start=12):
        rows.append({"match_date": f"2026-01-{i:02d}", "home_team": opp, "away_team": "Chelsea", "home_goals": 2, "away_goals": 0})
    rows.append({"match_date": "2026-02-20", "home_team": "Arsenal", "away_team": "Chelsea", "home_goals": 0, "away_goals": 9})
    frame = pd.DataFrame(rows)
    monkeypatch.setattr("football_prediction_v19.analysis.v2108_strength_band_performance_indicator._load_match_rows", lambda *args, **kwargs: frame)

    result = build_strength_band_performance_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-02-20", 0.4, 0.3, 0.3)

    assert result["sbp_home_target_opponent_zone"] in {"relegation_zone", "mid_table", "top_zone", "title_zone"}
    assert result["sbp_away_target_opponent_zone"] == "title_zone"
    assert result["sbp_home_ppg_vs_away_zone"] >= 0.0
    assert "sbp_strength_band_signal" in result
