import pandas as pd

from football_prediction_v19.analysis import v2104_draw_tendency_indicator as mod


def _rows():
    return pd.DataFrame(
        [
            {"match_date": f"2026-01-{day:02d}", "home_team": "Home", "away_team": f"X{day}", "home_goals": 1, "away_goals": 1}
            for day in range(1, 9)
        ]
        + [
            {"match_date": f"2026-01-{day:02d}", "home_team": f"Y{day}", "away_team": "Away", "home_goals": 2, "away_goals": 2}
            for day in range(1, 9)
        ]
        + [{"match_date": "2026-02-01", "home_team": "Home", "away_team": "Away", "home_goals": 5, "away_goals": 0}]
    )


def test_v2104_draw_tendency_counts_rates_and_excludes_match_date(monkeypatch):
    monkeypatch.setattr(mod, "_load_match_rows", lambda *args, **kwargs: _rows())
    result = mod.build_draw_tendency_indicator("League", "2025/26", "Home", "Away", "2026-02-01", 0.4, 0.3, 0.3)

    assert result["dt_indicator_quality"] == "FULL"
    assert result["dt_home_draws_before_match"] == 8
    assert result["dt_away_draws_before_match"] == 8
    assert result["dt_combined_draw_rate_before_match"] == 1.0
    assert result["dt_adjustment_applied"] is True
    assert result["dt_adjusted_draw_probability"] > 0.3


def test_v2104_draw_tendency_low_quality_no_adjustment(monkeypatch):
    monkeypatch.setattr(mod, "_load_match_rows", lambda *args, **kwargs: _rows().head(2))
    result = mod.build_draw_tendency_indicator("League", "2025/26", "Home", "Away", "2026-02-01", 0.4, 0.3, 0.3)

    assert result["dt_indicator_quality"] == "LOW"
    assert result["dt_adjustment_applied"] is False
    assert result["dt_adjusted_draw_probability"] == 0.3
