import pandas as pd

from football_prediction_v19.analysis.v27_evaluation_metrics import compute_v27_metrics
from scripts.generate_v2100_probability_explanation_report import generate_probability_explanation_report


def test_v2100_evaluation_summary_uses_probability_rows(tmp_path):
    rows = pd.DataFrame(
        [
            {
                "competition": "Premier League",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "home_win_probability": 0.43,
                "draw_probability": 0.31,
                "away_win_probability": 0.26,
                "top_probability_outcome": "HOME",
                "probability_edge": 0.12,
                "uncertainty_level": "MEDIUM",
                "evaluation_result": "HIT",
                "result_status": "RESOLVED",
            },
            {
                "competition": "Premier League",
                "home_team": "Team A",
                "away_team": "Team B",
                "home_win_probability": 0.30,
                "draw_probability": 0.28,
                "away_win_probability": 0.42,
                "top_probability_outcome": "AWAY",
                "probability_edge": 0.12,
                "uncertainty_level": "HIGH",
                "evaluation_result": "MISS",
                "result_status": "RESOLVED",
            },
        ]
    )

    metrics = compute_v27_metrics(rows)

    assert metrics["probability_rows_count"] == 2
    assert metrics["top_probability_hit_rate"] == 0.5
    assert metrics["top_probability_home_count"] == 1
    assert metrics["top_probability_away_count"] == 1
    assert "no_decision_count" in metrics
    assert "decision_count" in metrics


def test_v2100_probability_explanation_report_writes_outputs(tmp_path):
    rows_path = tmp_path / "rows.csv"
    pd.DataFrame(
        [
            {
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "home_win_probability": 0.43,
                "draw_probability": 0.31,
                "away_win_probability": 0.26,
                "top_probability_outcome": "HOME",
                "probability_edge": 0.12,
                "uncertainty_level": "MEDIUM",
                "evaluation_result": "HIT",
                "result_status": "RESOLVED",
                "base_probability_explanation": "Base model gives Home 43.00%, Draw 31.00%, Away 26.00%.",
                "goal_difference_shadow_explanation": "Goal difference before match favors Home.",
                "goals_for_shadow_explanation": "Goals For per match favors Home.",
                "goals_against_shadow_explanation": "Goals Against per match favors Home.",
                "signal_alignment_summary": "Signals supporting the top outcome: goal difference.",
                "signal_conflict_summary": "Signals in conflict: none clear.",
            }
        ]
    ).to_csv(rows_path, index=False)

    result = generate_probability_explanation_report(rows_path, tmp_path / "report")

    assert result["v2100_probability_explanation_report_status"] == "READY"
    assert result["probability_rows_count"] == 1
    assert result["top_probability_hit_rate"] == 1.0
    assert (tmp_path / "report" / "v2100_probability_explanation_rows.csv").exists()
    markdown = (tmp_path / "report" / "v2100_probability_explanation_report.md").read_text(encoding="utf-8")
    assert "v2.10.0 Probability Explanation Report" in markdown
    assert "No productive betting logic" in markdown
