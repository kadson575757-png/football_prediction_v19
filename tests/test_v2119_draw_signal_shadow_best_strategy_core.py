import pandas as pd

from football_prediction_v19.analysis.v2119_draw_signal_shadow_probe import choose_best_strategy


def test_v2119_best_strategy_tie_breakers():
    summary = pd.DataFrame([
        {"strategy_name": "a", "hit_rate": 0.50, "draw_recall": 0.20, "draw_false_count": 1, "evaluable_count": 10},
        {"strategy_name": "b", "hit_rate": 0.50, "draw_recall": 0.30, "draw_false_count": 2, "evaluable_count": 10},
        {"strategy_name": "c", "hit_rate": 0.50, "draw_recall": 0.30, "draw_false_count": 1, "evaluable_count": 9},
        {"strategy_name": "d", "hit_rate": 0.49, "draw_recall": 1.00, "draw_false_count": 0, "evaluable_count": 20},
    ])
    assert choose_best_strategy(summary)["strategy_name"] == "c"
