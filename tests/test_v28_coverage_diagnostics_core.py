import pandas as pd

from football_prediction_v19.analysis.v28_coverage_diagnostics import analyze_v27_coverage


def test_v28_coverage_diagnostics_core(tmp_path):
    rows = tmp_path / "rows.csv"
    pd.DataFrame(
        [
            {"competition": "A", "winner_analysis_status": "READY", "asof_guard_status": "CLEAN", "home_win_probability": 0.4, "draw_probability": 0.3, "away_win_probability": 0.3, "evaluation_result": "HIT", "result_status": "RESOLVED", "fixture_resolver_status": "RESOLVED"},
            {"competition": "A", "winner_analysis_status": "DATA_BLOCKED", "asof_guard_status": "", "home_win_probability": 0, "draw_probability": 0, "away_win_probability": 0, "evaluation_result": "DATA_BLOCKED", "result_status": "NOT_FOUND", "fixture_resolver_status": "NOT_FOUND", "resolver_reason": "No exact home/away fixture found"},
            {"competition": "B", "winner_analysis_status": "DATA_BLOCKED", "asof_guard_status": "", "home_win_probability": 0, "draw_probability": 0, "away_win_probability": 0, "evaluation_result": "DATA_BLOCKED", "result_status": "NOT_FOUND", "fixture_resolver_status": "NOT_FOUND", "resolver_reason": "No exact home/away fixture found"},
        ]
    ).to_csv(rows, index=False)

    summary = analyze_v27_coverage(rows)

    assert summary["ready_count"] == 1
    assert summary["data_blocked_count"] == 2
    assert summary["not_found_count"] == 2
    assert summary["recommendation"] == "USE_FIXTURE_SOURCE_SUPPORTED_SAMPLE_OR_ADD_LEAGUE_SOURCE_MAPPING"
    forbidden = {"roi", "profit", "yield", "stake", "bankroll"}
    allowed = {"roi_logic_enabled", "staking_logic_enabled"}
    assert not any(word in key.lower() and key not in allowed for key in summary for word in forbidden)

