import pandas as pd

from scripts.analyze_v2103_probability_calibration import analyze_probability_calibration, main


def test_v2103_probability_calibration_safety_flags_false(tmp_path):
    source = pd.DataFrame(
        [
            {
                "competition": "Premier League",
                "season": "2025/26",
                "home_team": "A",
                "away_team": "B",
                "match_date": "2026-03-01",
                "home_win_probability": 0.4,
                "draw_probability": 0.3,
                "away_win_probability": 0.3,
                "real_result": "HOME",
            }
        ]
    )

    result = analyze_probability_calibration(source, tmp_path)

    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False


def test_v2103_probability_calibration_console_safety_flags_false(tmp_path, capsys):
    rows = tmp_path / "rows.csv"
    pd.DataFrame(
        [
            {
                "competition": "Premier League",
                "season": "2025/26",
                "home_team": "A",
                "away_team": "B",
                "match_date": "2026-03-01",
                "home_win_probability": 0.4,
                "draw_probability": 0.3,
                "away_win_probability": 0.3,
                "real_result": "HOME",
            }
        ]
    ).to_csv(rows, index=False)

    assert main(["--rows", str(rows), "--output-dir", str(tmp_path / "out"), "--emit-all"]) == 0
    output = capsys.readouterr().out

    assert "automatic_betting_enabled=false" in output
    assert "staking_logic_enabled=false" in output
    assert "roi_logic_enabled=false" in output
