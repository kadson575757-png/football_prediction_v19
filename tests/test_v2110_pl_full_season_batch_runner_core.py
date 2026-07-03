import pandas as pd

from scripts.run_v2110_premier_league_2025_26_full_season_analysis import run_full_season_analysis


def _runner(**kwargs):
    if kwargs["home"] == "Broken FC":
        raise RuntimeError("boom")
    assert kwargs["as_of_date"] == "2025-08-15"
    assert "actual_result" not in kwargs
    return {
        "probability_analysis_status": "READY",
        "competition": kwargs["competition"],
        "season": kwargs["season"],
        "home_team": kwargs["home"],
        "away_team": kwargs["away"],
        "match_date": kwargs["match_date"],
        "as_of_date": kwargs["as_of_date"],
        "home_win_probability": 0.42,
        "draw_probability": 0.30,
        "away_win_probability": 0.28,
        "base_home_win_probability": 0.42,
        "base_draw_probability": 0.30,
        "base_away_probability": 0.28,
        "top_probability_outcome": "HOME",
        "probability_edge": 0.12,
        "probability_edge_band": "MEDIUM",
        "uncertainty_level": "MEDIUM",
        "data_quality_band": "PARTIAL",
        "asof_guard_status": "CLEAN",
        "leakage_warning": False,
        "automatic_betting_enabled": False,
        "staking_logic_enabled": False,
        "roi_logic_enabled": False,
    }


def test_v2110_full_season_batch_continues_after_single_match_failure(tmp_path):
    fixtures = pd.DataFrame([
        {"competition": "Premier League", "season": "2025/26", "match_date": "2025-08-16", "home_team": "Arsenal", "away_team": "Chelsea"},
        {"competition": "Premier League", "season": "2025/26", "match_date": "2025-08-16", "home_team": "Broken FC", "away_team": "Spurs"},
    ])

    result = run_full_season_analysis(fixtures, output_dir=tmp_path, runner=_runner)

    assert result["fixtures_analyzed"] == 2
    assert result["analysis_success_count"] == 1
    assert result["analysis_failed_count"] == 1
    rows = pd.read_csv(result["analysis_rows_csv_path"], keep_default_na=False)
    assert rows.loc[0, "as_of_date"] == "2025-08-15"
    assert rows.loc[0, "asof_guard_status"] == "CLEAN"
    assert rows.loc[0, "leakage_warning"] in [False, "False", "false"]

