import pandas as pd
import pytest

from football_prediction_v19.analysis.v2122_rolling_team_bias_shadow_probe import apply_shadow_strategy


def _ready_row():
    return {
        "actual_result": "DRAW", "top_probability_outcome": "HOME",
        "home_win_probability": 0.45, "draw_probability": 0.30, "away_win_probability": 0.25,
        "rolling_home_overprediction_delta": 0.20, "home_bias_history_quality": "READY",
        "rolling_away_overprediction_delta": 0.20, "away_bias_history_quality": "READY",
    }


def test_home_and_away_shadow_corrections_move_probability_to_draw():
    rows = pd.DataFrame([_ready_row()])
    home = apply_shadow_strategy(rows, "HOME_BIAS_002").iloc[0]
    assert home["shadow_home_win_probability"] == 0.43
    assert home["shadow_draw_probability"] == 0.32
    assert home["shadow_away_win_probability"] == pytest.approx(0.25)
    away = apply_shadow_strategy(rows, "AWAY_BIAS_001").iloc[0]
    assert away["shadow_home_win_probability"] == 0.45
    assert away["shadow_draw_probability"] == 0.31
    assert away["shadow_away_win_probability"] == pytest.approx(0.24)


def test_correction_is_not_applied_with_insufficient_history():
    row = _ready_row()
    row["home_bias_history_quality"] = "INSUFFICIENT_HISTORY"
    result = apply_shadow_strategy(pd.DataFrame([row]), "HOME_BIAS_002").iloc[0]
    assert not result["adjustment_applied"]
    assert result["shadow_home_win_probability"] == 0.45
