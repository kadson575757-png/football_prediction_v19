from scripts import run_match_winner_analysis
from tests.v25_test_helpers import fake_core_result


def test_v2100_emit_all_uses_probability_only_language(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("scripts.run_match_winner_analysis.run_v21_predict_winner", lambda **kwargs: fake_core_result())
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_home_away_ppg_indicator", lambda *args, **kwargs: {"indicator_quality": "LOW", "home_away_ppg_diff": 0})
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_last5_form_indicator", lambda *args, **kwargs: {"last5_indicator_quality": "LOW", "last5_points_diff": 0})
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_goal_difference_indicator", lambda *args, **kwargs: {"goal_difference_indicator_quality": "LOW", "goal_difference_diff": 0})
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_goals_for_indicator", lambda *args, **kwargs: {"goals_for_indicator_quality": "LOW", "goals_for_per_match_diff": 0})
    monkeypatch.setattr("scripts.run_match_winner_analysis.build_goals_against_indicator", lambda *args, **kwargs: {"goals_against_indicator_quality": "LOW", "goals_against_advantage_diff": 0})

    exit_code = run_match_winner_analysis.main(
        [
            "--competition", "Premier League",
            "--season", "2025/26",
            "--home", "Arsenal",
            "--away", "Chelsea",
            "--match-date", "2026-03-01",
            "--output-dir", str(tmp_path),
            "--emit-all",
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "NO_DECISION" not in output
    assert "DATA_BLOCKED" not in output
    assert "blocked by rule" not in output
    assert "Lean-only eligibility" not in output
    assert "decision strength" not in output
    assert "prediction_tier" not in output
    assert "WINNER_MODEL_PARTIAL" not in output
    assert "home_win_probability=" in output
    assert "draw_probability=" in output
    assert "away_win_probability=" in output
    assert "probability_summary=" in output
    assert "data_quality_notes=" in output
    assert "uncertainty_level=" in output
    assert "automatic_betting_enabled=false" in output
    assert "staking_logic_enabled=false" in output
    assert "roi_logic_enabled=false" in output
