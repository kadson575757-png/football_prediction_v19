from pathlib import Path
from scripts.run_match_winner_analysis import run_match_winner_analysis
from tests.v25_test_helpers import fake_core_result


def test_v25_runner_uses_winner_language_not_betting_language(monkeypatch, tmp_path):
    monkeypatch.setattr("scripts.run_match_winner_analysis.run_v21_predict_winner", lambda **kwargs: fake_core_result())
    result = run_match_winner_analysis(competition="Premier League", season="2025/26", home="Arsenal", away="Chelsea", match_date="2026-02-14", output_dir=tmp_path)
    text = Path(result["winner_analysis_markdown_path"]).read_text(encoding="utf-8").lower()
    assert "winner analysis" in text
    assert "tip" not in text
