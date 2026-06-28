import pandas as pd

from football_prediction_v19.analysis.v28_supported_sample_builder import build_supported_evaluation_sample


def test_v28_supported_sample_builder_smoke(monkeypatch, tmp_path):
    normalized = tmp_path / "football_data_live_normalized.csv"
    pd.DataFrame(
        [
            {"Date": "2026-03-01", "HomeTeam": "Arsenal", "AwayTeam": "Chelsea", "FTHG": 2, "FTAG": 1, "FTR": "H"},
            {"Date": "2026-03-08", "HomeTeam": "Chelsea", "AwayTeam": "Arsenal", "FTHG": 0, "FTAG": 1, "FTR": "A"},
            {"Date": "2026-03-15", "HomeTeam": "Liverpool", "AwayTeam": "Everton", "FTHG": "", "FTAG": "", "FTR": ""},
        ]
    ).to_csv(normalized, index=False)

    def fake_live_adapter(*args, **kwargs):
        assert kwargs["enable_network"] is False
        return {"football_data_live_status": "CACHE_HIT", "football_data_live_normalized_path": str(normalized)}

    monkeypatch.setattr("football_prediction_v19.analysis.v28_supported_sample_builder.run_football_data_live_adapter", fake_live_adapter)
    output = tmp_path / "sample.csv"
    result = build_supported_evaluation_sample("Premier League", "2025/26", target_matches=3, cache_only=True, enable_network=False, output_csv=output)

    frame = pd.read_csv(output, keep_default_na=False)
    assert result["matches_written"] == 2
    assert set(frame["home_team"]) == {"Arsenal", "Chelsea"}
    assert not ((frame["home_team"] == "Arsenal") & (frame["away_team"] == "Arsenal")).any()
    assert result["automatic_betting_enabled"] is False

