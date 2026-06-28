import pandas as pd

from scripts.run_match_winner_analysis import run_match_winner_analysis
from tests.v25_test_helpers import fake_core_result


def test_v26_runner_without_date_uses_network_fallback(monkeypatch, tmp_path):
    normalized = tmp_path / "football_data_live_normalized.csv"
    pd.DataFrame(
        [
            {"Date": "2026-03-01", "HomeTeam": "Arsenal", "AwayTeam": "Chelsea", "FTHG": "", "FTAG": "", "FTR": ""},
        ]
    ).to_csv(normalized, index=False)

    monkeypatch.setattr(
        "football_prediction_v19.analysis.v26_fixture_date_resolver.run_football_data_live_adapter",
        lambda *args, **kwargs: {"football_data_live_status": "SUCCESS", "football_data_live_normalized_path": str(normalized)},
    )
    monkeypatch.setattr("scripts.run_match_winner_analysis.run_v21_predict_winner", lambda **kwargs: fake_core_result())

    result = run_match_winner_analysis(
        competition="Premier League",
        season="2025/26",
        home="Arsenal",
        away="Chelsea",
        enable_network=True,
        output_dir=tmp_path / "out",
    )

    assert result["fixture_resolver_status"] == "RESOLVED"
    assert result["fixture_resolver_source"] == "football_data"
    assert result["match_date"] == "2026-03-01"
    assert result["as_of_date"] == "2026-02-28"
    assert result["asof_guard_status"] == "CLEAN"
    assert result["winner_analysis_status"] == "READY"
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
