import pandas as pd

from football_prediction_v19.analysis import v2105_clean_sheet_failed_to_score_indicator as mod


def _rows():
    return pd.DataFrame(
        [{"match_date": f"2026-01-{d:02d}", "home_team": "Home", "away_team": f"X{d}", "home_goals": 1, "away_goals": 0} for d in range(1, 9)]
        + [{"match_date": f"2026-01-{d:02d}", "home_team": f"Y{d}", "away_team": "Away", "home_goals": 2, "away_goals": 0} for d in range(1, 9)]
        + [{"match_date": "2026-02-01", "home_team": "Home", "away_team": "Away", "home_goals": 0, "away_goals": 9}]
    )


def test_v2105_clean_sheet_failed_to_score_rates_and_excludes_match_date(monkeypatch):
    monkeypatch.setattr(mod, "_load_match_rows", lambda *args, **kwargs: _rows())
    result = mod.build_clean_sheet_failed_to_score_indicator("League", "2025/26", "Home", "Away", "2026-02-01", 0.4, 0.3, 0.3)

    assert result["csfts_indicator_quality"] == "FULL"
    assert result["csfts_home_clean_sheet_rate"] == 1.0
    assert result["csfts_home_failed_to_score_rate"] == 0.0
    assert result["csfts_away_clean_sheet_rate"] == 0.0
    assert result["csfts_away_failed_to_score_rate"] == 1.0
    assert result["csfts_home_defensive_signal"] > result["csfts_away_defensive_signal"]
    assert round(result["csfts_adjusted_home_win_probability"] + result["csfts_adjusted_draw_probability"] + result["csfts_adjusted_away_probability"], 4) == 1.0
