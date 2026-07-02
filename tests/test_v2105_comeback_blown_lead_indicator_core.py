import pandas as pd

from football_prediction_v19.analysis import v2105_comeback_blown_lead_indicator as mod


def test_v2105_comeback_blown_lead_low_quality_without_halftime(monkeypatch):
    monkeypatch.setattr(
        mod,
        "_load_match_rows",
        lambda *args, **kwargs: pd.DataFrame([{"match_date": "2026-01-01", "home_team": "Home", "away_team": "Away", "home_goals": 1, "away_goals": 0}]),
    )
    result = mod.build_comeback_blown_lead_indicator("League", "2025/26", "Home", "Away", "2026-02-01", 0.4, 0.3, 0.3)

    assert result["cbl_indicator_quality"] == "LOW"
    assert result["cbl_adjustment_applied"] is False
    assert result["cbl_shadow_explanation"] == "Halftime/result-path data unavailable; no adjustment."
    assert result["cbl_adjusted_home_win_probability"] == 0.4
    assert result["cbl_adjusted_draw_probability"] == 0.3
    assert result["cbl_adjusted_away_probability"] == 0.3
