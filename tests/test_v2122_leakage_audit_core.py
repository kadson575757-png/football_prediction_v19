import pandas as pd

from football_prediction_v19.analysis.v2122_rolling_team_bias_shadow_probe import compute_rolling_team_bias_features


def test_asof_audit_has_no_post_match_sources():
    rows = pd.DataFrame([
        {"match_date": f"2025-02-{day:02d}", "home_team": "Alpha", "away_team": f"T{day}", "actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.50, "draw_probability": 0.28, "away_probability": 0.22}
        for day in range(1, 8)
    ])
    _, audit = compute_rolling_team_bias_features(rows)
    assert audit["post_match_rows_used_count"].sum() == 0
    assert set(audit["asof_audit_status"]) == {"CLEAN"}
    for _, row in audit[audit["max_source_date"].ne("")].iterrows():
        assert row["max_source_date"] < row["match_date"]
