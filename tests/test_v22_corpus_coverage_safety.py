from football_prediction_v19.analysis.v22_corpus_coverage_gate import run_v22_corpus_coverage_gate


def test_v22_corpus_coverage_safety(tmp_path):
    result = run_v22_corpus_coverage_gate(tmp_path / "gate")
    assert result["automatic_betting_enabled"] is False
    assert result["staking_logic_enabled"] is False
    assert result["roi_logic_enabled"] is False
