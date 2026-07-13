import pandas as pd

from football_prediction_v19.analysis.v2120_prediction_error_patterns import (
    classify_error_type,
    prepare_prediction_rows,
)


def test_error_type_and_prediction_hit_are_correct():
    assert classify_error_type("HOME", "DRAW") == "HOME_TOP_ACTUAL_DRAW"
    assert classify_error_type("AWAY", "HOME") == "AWAY_TOP_ACTUAL_HOME"
    assert classify_error_type("DRAW", "AWAY") == "DRAW_TOP_ACTUAL_AWAY"
    assert classify_error_type("HOME", "HOME") == "HIT"
    assert classify_error_type("", "HOME") == "UNKNOWN"

    prepared = prepare_prediction_rows(pd.DataFrame([
        {"actual_result": "HOME", "top_probability_outcome": "HOME"},
        {"actual_result": "DRAW", "top_probability_outcome": "AWAY"},
    ]))
    assert prepared["prediction_hit"].tolist() == [True, False]
    assert prepared["error_type"].tolist() == ["HIT", "AWAY_TOP_ACTUAL_DRAW"]
