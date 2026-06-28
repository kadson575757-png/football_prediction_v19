from football_prediction_v19.analysis.v28_supported_sample_builder import build_supported_evaluation_sample


def test_v28_safety_flags_false(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "football_prediction_v19.analysis.v28_supported_sample_builder.run_football_data_live_adapter",
        lambda *args, **kwargs: {"football_data_live_status": "DISABLED_NETWORK", "football_data_live_normalized_path": str(tmp_path / "missing.csv")},
    )
    result = build_supported_evaluation_sample("Premier League", "2025/26", target_matches=1, output_csv=tmp_path / "sample.csv")

    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
