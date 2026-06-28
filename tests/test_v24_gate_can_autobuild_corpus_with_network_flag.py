from football_prediction_v19.analysis.v24_winner_calibration_gate import run_v24_winner_calibration_gate


def test_v24_gate_can_autobuild_corpus_with_network_flag(monkeypatch, tmp_path):
    called = {"value": False}

    def fake_build(*args, **kwargs):
        called["value"] = True
        assert kwargs["enable_network"] is True
        return {"v22_real_season_corpus_status": "READY"}

    monkeypatch.setattr("football_prediction_v19.analysis.v24_winner_calibration_gate.build_real_season_corpus", fake_build)
    result = run_v24_winner_calibration_gate(tmp_path / "gate", tmp_path / "missing", {"matches_evaluated": 0}, enable_network=True)
    assert called["value"] is True
    assert result["auto_corpus_build_status"] == "READY"

