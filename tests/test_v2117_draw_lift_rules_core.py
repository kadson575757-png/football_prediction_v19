import pandas as pd

from football_prediction_v19.analysis.v2117_draw_bias_diagnostics import add_draw_rank, compute_draw_lift_rules


def test_v2117_draw_lift_rules_hypothetical_hit_rate_and_delta():
    rows = pd.DataFrame([
        {"actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.33, "draw_probability": 0.31, "away_win_probability": 0.36},
        {"actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.40, "draw_probability": 0.29, "away_win_probability": 0.31},
        {"actual_result": "AWAY", "top_probability_outcome": "AWAY", "home_win_probability": 0.20, "draw_probability": 0.30, "away_win_probability": 0.35},
    ])
    out = compute_draw_lift_rules(add_draw_rank(rows))
    rule_b = out[out["rule_name"].eq("DRAW_LIFT_B_028_GAP_005")].iloc[0]
    assert rule_b["candidate_count"] == 2
    assert rule_b["actual_draw_count"] == 1
    assert rule_b["precision"] == 0.5
    assert rule_b["hypothetical_top_hit_rate"] == round(2 / 3, 4)
    assert rule_b["delta_vs_baseline_top_hit_rate"] == 0.0
