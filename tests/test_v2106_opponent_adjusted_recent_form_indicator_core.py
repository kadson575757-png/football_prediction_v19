import pandas as pd

from football_prediction_v19.analysis.v2106_opponent_adjusted_recent_form_indicator import build_opponent_adjusted_recent_form_indicator


def _rows():
    return pd.DataFrame([
        {"match_date": f"2026-01-{day:02d}", "home_team": home, "away_team": away, "home_goals": hg, "away_goals": ag}
        for day, home, away, hg, ag in [
            (1, "Arsenal", "City", 2, 1), (2, "Arsenal", "Liverpool", 1, 0), (3, "Spurs", "Arsenal", 1, 2),
            (4, "Chelsea", "Arsenal", 0, 2), (5, "Arsenal", "United", 3, 1), (6, "Chelsea", "Luton", 1, 1),
            (7, "Burnley", "Chelsea", 2, 0), (8, "Chelsea", "Everton", 0, 1), (9, "Forest", "Chelsea", 1, 0),
            (10, "Chelsea", "Wolves", 1, 2), (11, "Arsenal", "Chelsea", 9, 9),
        ]
    ])


def test_opponent_adjusted_recent_form_shadow_fields(monkeypatch):
    monkeypatch.setattr("football_prediction_v19.analysis.v2106_opponent_adjusted_recent_form_indicator._load_match_rows", lambda *args, **kwargs: _rows())

    result = build_opponent_adjusted_recent_form_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-01-11", 0.4, 0.3, 0.3)

    assert result["indicator_name"] == "OPPONENT_ADJUSTED_RECENT_FORM"
    assert result["oarf_home_recent_points"] == 15
    assert result["oarf_away_recent_points"] == 1
    assert result["oarf_quality_adjusted_form_diff"] > 0
    assert result["oarf_adjustment_applied"] is True
    assert result["shadow_explanation"]
    assert result["oarf_shadow_explanation"]
    assert round(result["oarf_adjusted_home_win_probability"] + result["oarf_adjusted_draw_probability"] + result["oarf_adjusted_away_probability"], 6) == 1.0
