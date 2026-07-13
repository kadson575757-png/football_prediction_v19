import pandas as pd

from football_prediction_v19.analysis.v2124_pl_multi_season_robustness import evaluate_pl_multi_season_robustness


def test_missing_seasons_are_reported_and_other_seasons_continue(tmp_path):
    rows = pd.DataFrame([
        {"match_date": "2024-01-01", "as_of_date": "2023-12-31", "actual_result": "HOME", "top_probability_outcome": "HOME", "home_win_probability": 0.5, "draw_probability": 0.3, "away_probability": 0.2},
        {"match_date": "2024-01-02", "as_of_date": "2024-01-01", "actual_result": "DRAW", "top_probability_outcome": "HOME", "home_win_probability": 0.4, "draw_probability": 0.35, "away_probability": 0.25},
    ])
    result = evaluate_pl_multi_season_robustness(
        {"2023/24": rows},
        seasons=["2023/24", "2024/25", "2025/26"],
        season_load_info={"2024/25": {"load_status": "FAILED", "load_reason": "stub unavailable"}},
        expected_fixture_count=2,
        output_dir=tmp_path,
    )
    season_summary = pd.read_csv(tmp_path / "v2124_season_summary.csv", keep_default_na=False)
    assert result["seasons_evaluated"] == 1
    assert result["recommendation"] == "MULTI_SEASON_DATA_INSUFFICIENT"
    assert len(season_summary) == 3
    missing = season_summary.set_index("season").loc["2024/25"]
    assert missing["load_status"] == "FAILED"
    assert missing["load_reason"] == "stub unavailable"
