import pandas as pd

from football_prediction_v19.analysis.v2106_venue_recent_momentum_indicator import build_venue_recent_momentum_indicator


def test_venue_recent_momentum_shadow_fields(monkeypatch):
    rows = pd.DataFrame([
        {"match_date": f"2026-01-{i:02d}", "home_team": "Arsenal", "away_team": f"Away {i}", "home_goals": 2, "away_goals": 0}
        for i in range(1, 6)
    ] + [
        {"match_date": f"2026-01-{i + 5:02d}", "home_team": f"Home {i}", "away_team": "Chelsea", "home_goals": 2, "away_goals": 0}
        for i in range(1, 6)
    ] + [{"match_date": "2026-01-11", "home_team": "Arsenal", "away_team": "Chelsea", "home_goals": 9, "away_goals": 9}])
    monkeypatch.setattr("football_prediction_v19.analysis.v2106_venue_recent_momentum_indicator._load_match_rows", lambda *args, **kwargs: rows)

    result = build_venue_recent_momentum_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-01-11", 0.4, 0.3, 0.3)

    assert result["indicator_name"] == "VENUE_RECENT_MOMENTUM_PROFILE"
    assert result["vrm_home_recent_home_matches_count"] == 5
    assert result["vrm_away_recent_away_matches_count"] == 5
    assert result["vrm_venue_momentum_signal"] > 0
    assert result["vrm_adjustment_applied"] is True
    assert round(result["vrm_adjusted_home_win_probability"] + result["vrm_adjusted_draw_probability"] + result["vrm_adjusted_away_probability"], 6) == 1.0
