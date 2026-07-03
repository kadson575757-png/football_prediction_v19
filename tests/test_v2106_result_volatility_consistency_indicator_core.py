import pandas as pd

from football_prediction_v19.analysis.v2106_result_volatility_consistency_indicator import build_result_volatility_consistency_indicator


def test_result_volatility_consistency_shadow_fields(monkeypatch):
    rows = pd.DataFrame([
        {"match_date": f"2026-01-{i:02d}", "home_team": "Arsenal", "away_team": f"Away {i}", "home_goals": hg, "away_goals": ag}
        for i, hg, ag in [(1, 4, 0), (2, 0, 3), (3, 3, 1), (4, 1, 1), (5, 5, 2), (6, 0, 1)]
    ] + [
        {"match_date": f"2026-01-{i + 6:02d}", "home_team": "Chelsea", "away_team": f"Away C{i}", "home_goals": hg, "away_goals": ag}
        for i, hg, ag in [(1, 1, 0), (2, 1, 1), (3, 0, 1), (4, 2, 1), (5, 1, 2), (6, 0, 0)]
    ] + [{"match_date": "2026-01-13", "home_team": "Arsenal", "away_team": "Chelsea", "home_goals": 9, "away_goals": 9}])
    monkeypatch.setattr("football_prediction_v19.analysis.v2106_result_volatility_consistency_indicator._load_match_rows", lambda *args, **kwargs: rows)

    result = build_result_volatility_consistency_indicator("Premier League", "2025/26", "Arsenal", "Chelsea", "2026-01-13", 0.4, 0.3, 0.3)

    assert result["indicator_name"] == "RESULT_VOLATILITY_CONSISTENCY_PROFILE"
    assert result["rvc_home_goal_diff_std"] > result["rvc_away_goal_diff_std"]
    assert "rvc_combined_volatility_score" in result
    assert result["rvc_adjustment_applied"] in {True, False}
    assert round(result["rvc_adjusted_home_win_probability"] + result["rvc_adjusted_draw_probability"] + result["rvc_adjusted_away_probability"], 6) == 1.0
