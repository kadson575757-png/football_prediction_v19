from football_prediction_v19.analysis.v24_winner_calibration_gate import run_v24_winner_calibration_gate


def test_v24_gate_does_not_network_without_flag(monkeypatch, tmp_path):
    def fake_build(*args, **kwargs):
        raise AssertionError("network build should not run without enable_network")

    monkeypatch.setattr("football_prediction_v19.analysis.v24_winner_calibration_gate.build_real_season_corpus", fake_build)
    result = run_v24_winner_calibration_gate(tmp_path / "gate", tmp_path / "missing", {"matches_evaluated": 0})
    assert result["auto_corpus_build_status"] == "NOT_REQUESTED"
