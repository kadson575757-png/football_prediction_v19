import pandas as pd

from football_prediction_v19.analysis.v2124_pl_multi_season_robustness import evaluate_pl_multi_season_robustness


def test_asof_audit_rejects_sources_on_or_after_target(tmp_path):
    rows = pd.DataFrame([
        {"match_date": "2024-01-02", "as_of_date": "2024-01-01", "actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.5, "draw_probability": 0.3, "away_probability": 0.2},
        {"match_date": "2024-01-03", "as_of_date": "2024-01-03", "actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.4, "draw_probability": 0.35, "away_probability": 0.25},
    ])
    result = evaluate_pl_multi_season_robustness({"2023/24": rows}, seasons=["2023/24"], expected_fixture_count=2, output_dir=tmp_path)
    audit = pd.read_csv(tmp_path / "v2124_asof_audit.csv")
    assert audit["asof_clean"].tolist() == [True, False]
    assert result["post_match_rows_used_count"] == 0
