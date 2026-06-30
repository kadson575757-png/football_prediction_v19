import pandas as pd

from scripts.analyze_v2103_probability_calibration import (
    analyze_probability_calibration,
    build_calibration_rows,
    build_calibration_summary,
    build_bucket_summary,
)


def test_v2103_probability_calibration_core_metrics(tmp_path):
    source = pd.DataFrame(
        [
            _row(0.6, 0.2, 0.2, "HOME", "HOME"),
            _row(0.5, 0.3, 0.2, "HOME", "AWAY"),
            _row(0.2, 0.5, 0.3, "DRAW", "DRAW"),
        ]
    )

    rows = build_calibration_rows(source)
    known = rows[rows["real_result"].isin(["HOME", "DRAW", "AWAY"])]
    summary = build_calibration_summary(rows, known, build_bucket_summary(known))
    result = analyze_probability_calibration(source, tmp_path)

    assert list(rows["top_probability_hit"]) == [1, 0, 1]
    assert summary["multiclass_brier_score"] == 0.1778
    assert summary["top_probability_hit_rate"] == 0.6667
    assert summary["top_probability_average"] == 0.5333
    assert summary["calibration_gap"] == 0.1334
    assert summary["average_home_probability"] == 0.4333
    assert summary["actual_home_rate"] == 0.3333
    assert summary["home_probability_gap"] == -0.1
    assert summary["average_draw_probability"] == 0.3333
    assert summary["actual_draw_rate"] == 0.3333
    assert summary["draw_probability_gap"] == 0.0
    assert result["v2103_probability_calibration_status"] == "READY"


def _row(home, draw, away, top, real):
    return {
        "competition": "Premier League",
        "season": "2025/26",
        "home_team": "A",
        "away_team": "B",
        "match_date": "2026-03-01",
        "home_win_probability": home,
        "draw_probability": draw,
        "away_win_probability": away,
        "top_probability_outcome": top,
        "real_result": real,
        "probability_edge": 0.1,
        "probability_edge_band": "MEDIUM",
        "uncertainty_level": "LOW",
        "data_quality_band": "HIGH",
    }
